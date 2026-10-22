"""Regression checks for CFPB narrative data disappearing from an extract."""
from pathlib import Path
from src.model import fit_relief_model
from src.model_quality_research import generate_real_predictions
import numpy as np
import pandas as pd


def make_model_data(rows=100):
    return pd.DataFrame({
        "complaint_id": [str(i) for i in range(rows)],
        "date_received": pd.date_range("2025-01-01", periods=rows),
        "company": ["A" if i % 2 else "B" for i in range(rows)],
        "product": ["Credit" if i % 3 else "Mortgage" for i in range(rows)],
        "sub_product": "Unknown",
        "issue": ["Issue A" if i % 2 else "Issue B" for i in range(rows)],
        "state": ["VA" if i % 2 else "MD" for i in range(rows)],
        "submitted_via": "Web",
        "has_narrative": [i % 2 for i in range(rows)],
        "has_relief": [int(i % 3 == 0) for i in range(rows)],
    })


def synthetic_complaints(n=400):
    rng = np.random.default_rng(45)
    frame = make_model_data(n)
    frame["company"] = rng.choice(["A", "B", "C"], n)
    frame["has_relief"] = rng.integers(0, 2, n)
    return frame


def test_original_excludes_constant_zero_narrative(tmp_path: Path):
    frame = make_model_data(100)
    frame["has_narrative"] = 0
    report = fit_relief_model(frame, tmp_path / "model.json")
    assert report["status"] == "completed"
    assert "has_narrative" not in report["features"]
    assert "has_narrative" in report["excluded_features"]
    assert report["narrative_feature_audit"]["train_positive_rows"] == 0
    assert report["narrative_feature_audit"]["sample_positive_rows"] == 0


def test_original_retains_varying_narrative(tmp_path: Path):
    frame = make_model_data(100)
    report = fit_relief_model(frame, tmp_path / "model.json")
    assert report["status"] == "completed"
    assert "has_narrative" in report["features"]
    assert report["excluded_features"] == []


def test_research_excludes_constant_narrative(tmp_path: Path):
    frame = synthetic_complaints(400)
    frame["has_narrative"] = 0
    meta = generate_real_predictions(frame, tmp_path / "preds.csv")
    assert "has_narrative" not in meta["features"]
    assert "has_narrative" in meta["excluded_features"]
    assert meta["narrative_feature_audit"]["sample_positive_rows"] == 0
    assert meta["counts"]["test"] >= 30


def test_research_retains_varying_narrative(tmp_path: Path):
    meta = generate_real_predictions(synthetic_complaints(400), tmp_path / "preds.csv")
    assert "has_narrative" in meta["features"]
    assert meta["excluded_features"] == []


def test_research_does_not_choose_feature_based_on_future_period(tmp_path: Path):
    frame = synthetic_complaints(400)
    frame["has_narrative"] = 0
    frame.loc[350:, "has_narrative"] = 1
    meta = generate_real_predictions(frame, tmp_path / "preds.csv")
    assert "has_narrative" in meta["excluded_features"]
    assert meta["narrative_feature_audit"]["sample_positive_rows"] == 50
    assert meta["narrative_feature_audit"]["train_positive_rows"] == 0


def test_original_excludes_constant_one_narrative(tmp_path: Path):
    frame = make_model_data(100)
    frame["has_narrative"] = 1
    report = fit_relief_model(frame, tmp_path / "model.json")
    assert report["status"] == "completed"
    assert report["narrative_feature_audit"]["train_unique_values"] == 1
    assert "has_narrative" in report["excluded_features"]
