"""Optional, offline CFPB historical-narrative retrieval and text benchmark.

This module is intentionally separate from the structured-complaint pipeline.
It never downloads narratives or modifies the existing DuckDB/Parquet artifacts.
"""

from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.pipeline import make_pipeline

TEXT = "complaint_what_happened"
REQUIRED = ("complaint_id", "date_received", "product", TEXT)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _csv_chunks(path: Path, chunk_size: int = 10_000) -> Iterator[pd.DataFrame]:
    """Read a CSV or an official archive ZIP without expanding it on disk."""
    if path.suffix.lower() == ".csv":
        yield from pd.read_csv(path, dtype=str, chunksize=chunk_size)
    elif path.suffix.lower() == ".zip":
        with ZipFile(path) as archive:
            names = sorted(
                name for name in archive.namelist()
                if name.lower().endswith(".csv") and not name.startswith("__MACOSX/")
            )
            if not names:
                raise ValueError("Archive ZIP contains no CSV files")
            for name in names:
                with archive.open(name) as source:
                    yield from pd.read_csv(source, dtype=str, chunksize=chunk_size)
    else:
        raise ValueError("Expected an existing .csv or .zip file")


def _normalized_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "Complaint ID": "complaint_id",
        "Date received": "date_received",
        "Product": "product",
        "Consumer complaint narrative": TEXT,
        "consumer_narrative": TEXT,
    }
    frame = chunk.rename(columns=aliases)
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise ValueError(f"Source is missing narrative columns: {missing}")
    frame = frame[list(REQUIRED)].copy()
    for column in REQUIRED:
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    frame[TEXT] = frame[TEXT].str.replace(r"\s+", " ", regex=True)
    frame["date_received"] = pd.to_datetime(
        frame["date_received"], errors="coerce", utc=True
    ).dt.tz_localize(None)
    return frame


def _fingerprint(value: str) -> str:
    """Normalize trivial punctuation/spacing variants of the same narrative."""
    normalized = re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_narratives(
    path: str | Path,
    *,
    max_rows: int = 5_000,
    min_chars: int = 40,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Deterministically sample eligible historical narratives using a reservoir.

    Sampling scans the ENTIRE selected file so records are not simply the first
    5,000 (often a short time interval). Only the bounded reservoir is held.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if max_rows < 1 or min_chars < 1:
        raise ValueError("max_rows and min_chars must be positive")
    rng = random.Random(seed)
    reservoir: list[dict[str, object]] = []
    seen = 0
    total = 0
    for chunk in _csv_chunks(path):
        total += len(chunk)
        frame = _normalized_chunk(chunk)
        usable = frame[
            frame[TEXT].str.len().ge(min_chars)
            & frame["complaint_id"].ne("")
            & frame["product"].ne("")
            & frame["date_received"].notna()
        ]
        for row in usable.to_dict("records"):
            seen += 1
            if len(reservoir) < max_rows:
                reservoir.append(row)
            else:
                position = rng.randrange(seen)
                if position < max_rows:
                    reservoir[position] = row
    if not reservoir:
        raise ValueError(
            "No usable complaint narratives; the current CFPB API/structured "
            "sample may not contain narrative text. Use the historical archive."
        )
    frame = pd.DataFrame(reservoir)
    selected_before_dedup = len(frame)
    frame = (
        frame.sort_values(["date_received", "complaint_id"])
        .drop_duplicates(subset="complaint_id", keep="last")
        .assign(_text_hash=lambda df: df[TEXT].map(_fingerprint))
        .drop_duplicates(subset="_text_hash", keep="first")
        .drop(columns="_text_hash")
        .reset_index(drop=True)
    )
    audit = {
        "source_filename": path.name,
        "source_sha256": _file_hash(path),
        "sampling_method": "seeded_reservoir_over_nonempty_narratives",
        "sampling_seed": seed,
        "source_rows_scanned": total,
        "eligible_narrative_rows": seen,
        "sampled_before_dedup": selected_before_dedup,
        "selected_after_dedup": len(frame),
        "duplicate_ids_or_text_removed": selected_before_dedup - len(frame),
        "min_chars": min_chars,
        "min_received_date": frame["date_received"].min().date().isoformat(),
        "max_received_date": frame["date_received"].max().date().isoformat(),
    }
    return frame, audit


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _embeddings(encoder: object, texts: list[str]) -> np.ndarray:
    result = np.asarray(
        encoder.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        ),
        dtype=float,
    )
    if result.ndim != 2 or result.shape[0] != len(texts):
        raise ValueError("Embedding model returned an invalid matrix shape")
    if not np.isfinite(result).all():
        raise ValueError("Embedding model returned non-finite values")
    lengths = np.linalg.norm(result, axis=1, keepdims=True)
    if np.any(lengths <= 0):
        raise ValueError("Embedding model returned a zero vector")
    return result / lengths


def semantic_search(
    frame: pd.DataFrame, query: str, encoder: object, *, top_k: int = 5
) -> list[dict[str, object]]:
    """Exact cosine retrieval; top-k returned in descending similarity order."""
    if not query or not query.strip():
        raise ValueError("Query must not be empty")
    if top_k < 1 or frame.empty:
        raise ValueError("top_k and nonempty documents are required")
    docs = _embeddings(encoder, frame[TEXT].astype(str).tolist())
    q = _embeddings(encoder, [query.strip()])[0]
    similarities = docs @ q
    ranked = np.argsort(-similarities, kind="stable")[:top_k]
    return [
        {
            "complaint_id": str(frame.iloc[i]["complaint_id"]),
            "date_received": str(frame.iloc[i]["date_received"].date()),
            "product": str(frame.iloc[i]["product"]),
            "similarity": round(float(similarities[i]), 5),
            "narrative": str(frame.iloc[i][TEXT]),
        }
        for i in ranked
    ]


def _time_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    ordered = frame.sort_values(["date_received", "complaint_id"])
    dates = sorted(ordered["date_received"].dt.normalize().unique())
    if len(dates) < 4:
        raise ValueError("Need at least four different received dates for a temporal split")
    cutoff = dates[int(0.75 * len(dates))]
    train = ordered[ordered["date_received"].dt.normalize() < cutoff].copy()
    test = ordered[ordered["date_received"].dt.normalize() >= cutoff].copy()
    if len(train) < 15 or len(test) < 6:
        raise ValueError("Need at least 15 training and 6 test narratives")
    return train, test, pd.Timestamp(cutoff).date().isoformat()


def _remove_near_duplicates(
    train: pd.DataFrame, test: pd.DataFrame, *, threshold: float = 0.98
) -> tuple[pd.DataFrame, int]:
    """Exclude nearly identical test texts using train-fitted char n-gram similarity."""
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(3, 5), max_features=20_000
    )
    train_matrix = vectorizer.fit_transform(train[TEXT].tolist())
    test_matrix = vectorizer.transform(test[TEXT].tolist())
    maxima: list[float] = []
    for start in range(0, len(test), 128):
        similarities = test_matrix[start : start + 128] @ train_matrix.T
        maxima.extend(np.asarray(similarities.max(axis=1).toarray()).ravel())
    keep = np.asarray(maxima) < threshold
    return test.iloc[np.flatnonzero(keep)].copy(), int((~keep).sum())


def _metrics(y_true: pd.Series, predictions: np.ndarray, labels: list[str]) -> dict:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, predictions, labels=labels, zero_division=0
    )
    return {
        "accuracy": round(float(accuracy_score(y_true, predictions)), 5),
        "macro_f1": round(float(f1_score(y_true, predictions, labels=labels, average="macro", zero_division=0)), 5),
        "by_class": {
            label: {
                "precision": round(float(precision[i]), 5),
                "recall": round(float(recall[i]), 5),
                "f1": round(float(f1[i]), 5),
                "support": int(support[i]),
            }
            for i, label in enumerate(labels)
        },
        "confusion_matrix": confusion_matrix(
            y_true, predictions, labels=labels
        ).tolist(),
    }


def classification_benchmark(
    frame: pd.DataFrame,
    encoder: object,
    *,
    min_train_class: int = 5,
    max_classes: int = 5,
) -> dict[str, object]:
    """Chronological, train-only label selection; no model tuning on the test set."""
    if min_train_class < 2 or max_classes < 2:
        raise ValueError("min_train_class and max_classes must each be >= 2")
    train, test, cutoff = _time_split(frame)
    counts = train["product"].value_counts()
    eligible = counts[counts >= min_train_class].head(max_classes).index.tolist()
    if len(eligible) < 2:
        raise ValueError("Not enough adequately represented training product classes")
    labels = sorted(eligible)
    train = train[train["product"].isin(labels)].copy()
    test = test[test["product"].isin(labels)].copy()
    if test.empty or test["product"].nunique() < 2:
        raise ValueError("Temporal test period has fewer than two eligible product classes")
    test_before_duplicate_audit = len(test)
    test, near_duplicate_count = _remove_near_duplicates(train, test)
    if len(test) < 5 or test["product"].nunique() < 2:
        raise ValueError("Too few independent test narratives after near-duplicate filtering")
    x_train = train[TEXT].tolist()
    x_test = test[TEXT].tolist()
    y_train = train["product"]
    y_test = test["product"]

    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(np.zeros((len(train), 1)), y_train)
    baseline_pred = baseline.predict(np.zeros((len(test), 1)))

    lexical = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=30_000),
        LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42),
    )
    lexical.fit(x_train, y_train)
    lexical_pred = lexical.predict(x_test)

    train_emb = _embeddings(encoder, x_train)
    test_emb = _embeddings(encoder, x_test)
    semantic = LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=42
    )
    semantic.fit(train_emb, y_train)
    semantic_pred = semantic.predict(test_emb)

    return {
        "task": "product_classification_from_public_narrative_text",
        "split": "chronological_by_received_date",
        "test_starts": cutoff,
        "classes_selected_from_training_only": labels,
        "training_label_distribution": {
            str(k): int(v) for k, v in y_train.value_counts().items()
        },
        "test_label_distribution": {
            str(k): int(v) for k, v in y_test.value_counts().items()
        },
        "train_rows": len(train),
        "test_rows_before_near_duplicate_filter": test_before_duplicate_audit,
        "test_rows": len(test),
        "near_duplicate_test_rows_excluded": near_duplicate_count,
        "near_duplicate_cosine_threshold": 0.98,
        "model_results": {
            "most_frequent_baseline": _metrics(y_test, baseline_pred, labels),
            "tfidf_logistic_regression": _metrics(y_test, lexical_pred, labels),
            "embedding_logistic_regression": _metrics(y_test, semantic_pred, labels),
        },
        "limitations": [
            "Label selection uses training data only; class coverage is not the full CFPB taxonomy.",
            "Historical published narratives are an opt-in, nonrepresentative subset.",
            "Near-duplicate filtering is heuristic; paraphrases may remain.",
            "Results are exploratory and should be repeated across independent periods.",
        ],
    }
