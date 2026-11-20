"""Offline NLP tests: no network calls or pretrained model downloads."""

from __future__ import annotations

from zipfile import ZipFile

import numpy as np
import pandas as pd
import pytest

from scripts.make_nlp_fixture import create_fixture
from src.nlp import (
    TEXT,
    _remove_near_duplicates,
    classification_benchmark,
    load_narratives,
    semantic_search,
)


class MockEncoder:
    """Deterministic, test-only vectors; NOT a language embedding model."""

    vocabulary = (
        "mortgage", "escrow", "home", "loan", "card", "credit", "charge",
        "debt", "collector", "collection", "payment", "fee", "balance",
    )

    def encode(self, texts, **_kwargs):
        vectors = []
        for text in texts:
            tokens = str(text).casefold()
            vector = np.asarray(
                [tokens.count(word) for word in self.vocabulary], dtype=float
            )
            vector[-1] += 0.1  # protect against all-zero, mock-only examples
            vectors.append(vector)
        return np.vstack(vectors)


def test_reservoir_loader_is_deterministic_and_deduplicates(tmp_path):
    fixture = tmp_path / "fiction.csv"
    create_fixture(fixture)
    first, meta = load_narratives(fixture, max_rows=30, seed=17)
    second, _ = load_narratives(fixture, max_rows=30, seed=17)
    assert first["complaint_id"].tolist() == second["complaint_id"].tolist()
    assert meta["source_rows_scanned"] == 72
    assert meta["eligible_narrative_rows"] == 72
    assert meta["source_sha256"]
    assert first["complaint_id"].is_unique
    assert len(first) <= 30


def test_official_columns_and_zip_streaming(tmp_path):
    archive = tmp_path / "archive.zip"
    csv_text = (
        "Complaint ID,Date received,Product,Consumer complaint narrative\n"
        '123,2024-01-01,Mortgage,"The escrow balance does not match my statements."\n'
        '124,2024-02-01,Credit card,"My card shows a fee even after I paid the balance."\n'
    )
    with ZipFile(archive, "w") as z:
        z.writestr("year/complaints.csv", csv_text)
    frame, audit = load_narratives(archive, min_chars=20)
    assert len(frame) == 2
    assert audit["source_rows_scanned"] == 2
    assert set(frame["complaint_id"]) == {"123", "124"}


def test_missing_narratives_fails_explicitly(tmp_path):
    csv = tmp_path / "missing.csv"
    pd.DataFrame({
        "complaint_id": ["1"],
        "date_received": ["2025-01-01"],
        "product": ["Mortgage"],
        "complaint_what_happened": [""],
    }).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="No usable complaint narratives"):
        load_narratives(csv)


def test_missing_required_column_fails_explicitly(tmp_path):
    csv = tmp_path / "invalid.csv"
    pd.DataFrame({"complaint_id": ["1"]}).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="missing narrative columns"):
        load_narratives(csv)


def test_invalid_limits_and_extension(tmp_path):
    csv = tmp_path / "fixture.csv"
    create_fixture(csv)
    with pytest.raises(ValueError, match="positive"):
        load_narratives(csv, max_rows=0)
    source = tmp_path / "file.txt"
    source.write_text("not csv", encoding="utf-8")
    with pytest.raises(ValueError, match="csv or .zip"):
        load_narratives(source)


def test_semantic_search_ranks_known_vector_and_validates_query(tmp_path):
    fixture = tmp_path / "fixture.csv"
    create_fixture(fixture)
    frame, _ = load_narratives(fixture)
    results = semantic_search(frame, "escrow mortgage home loan", MockEncoder(), top_k=4)
    assert len(results) == 4
    assert all("narrative" in result for result in results)
    assert results[0]["product"] == "Mortgage"
    assert results[0]["similarity"] >= results[-1]["similarity"]
    with pytest.raises(ValueError, match="empty"):
        semantic_search(frame, " ", MockEncoder())
    with pytest.raises(ValueError, match="top_k"):
        semantic_search(frame, "Mortgage", MockEncoder(), top_k=0)


def test_chronological_benchmark_exposes_real_metrics(tmp_path):
    fixture = tmp_path / "fixture.csv"
    create_fixture(fixture)
    frame, _ = load_narratives(fixture)
    result = classification_benchmark(frame, MockEncoder())
    assert result["train_rows"] > 15
    assert result["test_rows"] >= 5
    assert result["test_starts"] > "2024-01-01"
    assert len(result["classes_selected_from_training_only"]) == 3
    for key in (
        "most_frequent_baseline", "tfidf_logistic_regression",
        "embedding_logistic_regression",
    ):
        metrics = result["model_results"][key]
        assert 0 <= metrics["macro_f1"] <= 1
        assert 0 <= metrics["accuracy"] <= 1
        assert len(metrics["confusion_matrix"]) == 3
        assert sum(v["support"] for v in metrics["by_class"].values()) == result["test_rows"]


def test_near_duplicate_filter_catches_punctuation_variants():
    train = pd.DataFrame({
        TEXT: ["My mortgage payment was incorrectly applied to my loan balance"]
    })
    test = pd.DataFrame({
        TEXT: [
            "My mortgage payment was incorrectly applied to my loan balance!",
            "The collector contacted me about a debt I never owed or opened",
        ]
    })
    filtered, removed = _remove_near_duplicates(train, test)
    assert removed == 1
    assert len(filtered) == 1


def test_unsupported_training_labels_fail(tmp_path):
    fixture = tmp_path / "fixture.csv"
    create_fixture(fixture)
    frame, _ = load_narratives(fixture)
    frame["product"] = "Mortgage"
    with pytest.raises(ValueError, match="Not enough"):
        classification_benchmark(frame, MockEncoder())


def test_duplicate_id_and_narrative_text_are_excluded(tmp_path):
    csv = tmp_path / "repeated.csv"
    pd.DataFrame({
        "complaint_id": ["100", "100", "101", "102"],
        "date_received": ["2024-01-01", "2024-01-01", "2024-01-03", "2024-01-04"],
        "product": ["Mortgage"] * 4,
        TEXT: [
            "My loan is fully repaid but the bank still lists a balance due.",
            "My loan is fully repaid but the bank still lists a balance due.",
            "My loan is fully repaid, but the bank still lists a balance due!",
            "The mortgage servicer charged me for insurance twice this month.",
        ],
    }).to_csv(csv, index=False)
    frame, info = load_narratives(csv, min_chars=10)
    assert len(frame) == 2
    assert info["duplicate_ids_or_text_removed"] == 2


def test_cli_writes_aggregate_only_and_marks_synthetic(tmp_path, monkeypatch):
    import json
    import sys
    from types import SimpleNamespace
    from scripts import run_nlp

    csv = tmp_path / "fixture.csv"
    output = tmp_path / "metrics.json"
    create_fixture(csv)
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(
        SentenceTransformer=lambda model: MockEncoder()
    ))
    monkeypatch.setattr(sys, "argv", [
        "run_nlp", "--data", str(csv), "--source-kind", "synthetic",
        "--benchmark", "--out", str(output), "--query", "loan balance",
    ])
    run_nlp.main()
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["source_kind"] == "synthetic"
    assert result["note"] == "Synthetic demonstration"
    assert result["evaluation"]["test_rows"] > 0
    assert "complaint_what_happened" not in output.read_text(encoding="utf-8")
