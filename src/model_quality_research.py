"""Leakage-aware *additional* CFPB model experiment with a three-way temporal split.

Retains the existing 75/25 model untouched. The research experiment fits an
identically specified logistic-regression pipeline on the earlier 60% of rows,
reserves approximately 15% for calibration/threshold selection, and evaluates
on the most recent approximately 25%. Boundary days are never split.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from cfpb_quality.report import create_report
from cfpb_quality.validation import validate_predictions

CATEGORICAL_FEATURES = (
    "company", "product", "sub_product", "issue", "state", "submitted_via"
)
BINARY_FEATURES = ("has_narrative",)
FEATURES = list(CATEGORICAL_FEATURES + BINARY_FEATURES)
REQUIRED_COLUMNS = set(FEATURES) | {"complaint_id", "date_received", "has_relief"}


def make_research_pipeline(*, include_narrative: bool = True) -> Pipeline:
    """Mirror the original model while excluding train-constant narrative flags."""
    transformers = [
        (
            "category",
            OneHotEncoder(handle_unknown="ignore", min_frequency=5),
            list(CATEGORICAL_FEATURES),
        ),
    ]
    if include_narrative:
        transformers.append(("binary", "passthrough", list(BINARY_FEATURES)))
    return Pipeline(
        [
            (
                "encode",
                ColumnTransformer(transformers),
            ),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )


def prepare_research_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize *processed* complaint data; refuse unsafe or ambiguous labels."""
    absent = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if absent:
        raise ValueError(
            "Expected cleaned complaints (e.g. data/processed/complaints.parquet). "
            f"Missing: {absent}"
        )
    df = frame.copy()
    if df["complaint_id"].isna().any():
        raise ValueError("Missing complaint_id values")
    df["complaint_id"] = df["complaint_id"].astype(str).str.strip()
    if df["complaint_id"].eq("").any() or df["complaint_id"].duplicated().any():
        raise ValueError("Blank or repeated complaint_id; ensure one row per complaint")
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce", utc=True)
    if df["date_received"].isna().any():
        raise ValueError("Missing or invalid date_received")
    if df["has_relief"].isna().any():
        raise ValueError("Missing relief labels")
    labels = pd.to_numeric(df["has_relief"], errors="coerce")
    if labels.isna().any() or not labels.isin([0, 1]).all():
        raise ValueError("has_relief must be binary 0/1")
    df["has_relief"] = labels.astype(int)
    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].fillna("Unknown").astype(str)
    binary = pd.to_numeric(df["has_narrative"].fillna(0), errors="coerce")
    if binary.isna().any() or not binary.isin([0, 1]).all():
        raise ValueError("has_narrative must be binary 0/1")
    df["has_narrative"] = binary.astype(int)
    return df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)


def assign_temporal_splits(df: pd.DataFrame, *, minimum_rows: int = 160) -> pd.DataFrame:
    """Split approximately 60/15/25 by row count, never splitting one date.

    If a concentration on a few days prevents a useful partition, reject it
    instead of producing overlapping or tiny calibration periods.
    """
    if len(df) < minimum_rows:
        raise ValueError(f"Need at least {minimum_rows} cleaned rows for three-way evaluation; found {len(df)}")
    days = df["date_received"].dt.normalize()
    day_sizes = days.value_counts().sort_index()
    if len(day_sizes) < 6:
        raise ValueError("Need at least six distinct received dates")
    cumulative = day_sizes.cumsum().to_numpy()
    first = int(np.searchsorted(cumulative, 0.60 * len(df), side="left"))
    second = int(np.searchsorted(cumulative, 0.75 * len(df), side="left"))
    if first >= second or second >= len(day_sizes) - 1:
        raise ValueError("Cannot create distinct chronological train/validation/test windows")
    split = np.where(
        days <= day_sizes.index[first],
        "train",
        np.where(days <= day_sizes.index[second], "validation", "test"),
    )
    result = df.copy()
    result["split"] = split
    counts = result["split"].value_counts().to_dict()
    if counts.get("train", 0) < 80 or counts.get("validation", 0) < 30 or counts.get("test", 0) < 30:
        raise ValueError(f"Chronological windows too small for valid diagnostics: {counts}")
    for name in ("train", "validation", "test"):
        if result.loc[result["split"] == name, "has_relief"].nunique() < 2:
            raise ValueError(f"Both outcomes required in the {name} period")
    return result


def generate_real_predictions(frame: pd.DataFrame, csv_path: str | Path) -> dict:
    """Train only on earlier rows and write a local-only predictions file.

    In-sample training probabilities are exported only because the model-quality
    report uses the training labels to define a prevalence-only benchmark.
    They are not used to evaluate model performance or tune the calibrator.
    """
    ordered = assign_temporal_splits(prepare_research_data(frame))
    train = ordered[ordered["split"] == "train"]
    include_narrative = train["has_narrative"].nunique(dropna=False) > 1
    selected_features = list(CATEGORICAL_FEATURES)
    if include_narrative:
        selected_features.extend(BINARY_FEATURES)
    excluded_features = sorted(set(FEATURES) - set(selected_features))
    model = make_research_pipeline(include_narrative=include_narrative)
    model.fit(train[selected_features], train["has_relief"])
    parts = []
    for name in ("train", "validation", "test"):
        part = ordered[ordered["split"] == name]
        scores = model.predict_proba(part[selected_features])[:, 1]
        parts.append(pd.DataFrame({
            "complaint_id": part["complaint_id"].values,
            "date_received": part["date_received"].dt.strftime("%Y-%m-%d").values,
            "split": name,
            "y_true": part["has_relief"].values,
            "y_prob": scores,
            "product": part["product"].values,
            "company": part["company"].values,
        }))
    predictions = pd.concat(parts, ignore_index=True)
    validate_predictions(predictions)  # assert temporal integrity before writing
    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(path, index=False)
    return {
        "status": "completed",
        "experiment": "research_three_way_60_15_25_approx_by_date",
        "model": "logistic_regression_balanced_weight_onehot_min_frequency_5",
        "features": selected_features,
        "excluded_features": excluded_features,
        "narrative_feature_audit": {
            "train_positive_rows": int(train["has_narrative"].sum()),
            "sample_positive_rows": int(ordered["has_narrative"].sum()),
            "train_unique_values": int(train["has_narrative"].nunique()),
            "interpretation": (
                "Excluded: constant in training; missing source narrative content "
                "does not prove complainants did not submit narratives"
                if not include_narrative else "Retained: varies in training"
            ),
        },
        "rows": int(len(predictions)),
        "counts": {name: int((predictions["split"] == name).sum())
                   for name in ("train", "validation", "test")},
        "split_policy": "chronological by date_received; same-day records never cross windows",
        "label": "has_relief, derived from company_response (post-intake outcome)",
        "caveat": "This is not the repository's original 75/25 experiment; do not compare metric changes as model improvements.",
    }


def run_real_evaluation(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    min_group_n: int = 50,
    minimum_recall: float = 0.8,
    data_kind: str = "unverified",
) -> dict:
    """Fit new research model, export actual holdout scores, report diagnostics."""
    out = Path(output_dir)
    csv = out / "real_holdout_predictions.csv"
    metadata = generate_real_predictions(frame, csv)
    report = create_report(
        csv,
        out,
        min_group_n=min_group_n,
        minimum_recall=minimum_recall,
        calibrate=True,
        data_kind=data_kind,
    )
    (out / "research_experiment.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return {"metadata": metadata, "report": report}
