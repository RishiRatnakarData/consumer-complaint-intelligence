"""End-to-end temporal evaluation tests using intentionally synthetic fixture rows."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.model_quality_research import (
    FEATURES,
    assign_temporal_splits,
    generate_real_predictions,
    prepare_research_data,
    run_real_evaluation,
)
from cfpb_quality.validation import validate_predictions


def synthetic_complaints(n=400):
    rng = np.random.default_rng(45)
    month = pd.date_range("2025-01-01", periods=n, freq="D")
    product = rng.choice(["Mortgage", "Credit card", "Credit reporting"], n)
    issue = rng.choice(["Incorrect information", "Payment processing"], n)
    company = rng.choice(["A", "B", "C"], n)
    has_narrative = rng.integers(0, 2, n)
    probability = 1 / (1 + np.exp(-(
        -0.65 + 0.55 * (product == "Mortgage")
        + 0.25 * (company == "A") + 0.5 * has_narrative
    )))
    labels = rng.binomial(1, probability)
    return pd.DataFrame({
        "complaint_id": [f"id_{i:05}" for i in range(n)],
        "date_received": month,
        "company": company,
        "product": product,
        "sub_product": "Unknown",
        "issue": issue,
        "state": rng.choice(["VA", "MD"], n),
        "submitted_via": "Web",
        "has_narrative": has_narrative,
        "has_relief": labels,
        "company_response": ["Closed with relief" if x else "Closed with explanation" for x in labels],
    })


def test_integrated_fit_and_report(tmp_path: Path):
    result = run_real_evaluation(synthetic_complaints(), tmp_path / "evaluation", min_group_n=10, data_kind="unverified")
    counts = result["metadata"]["counts"]
    assert sum(counts.values()) == 400
    assert all(v >= 30 for v in counts.values())
    assert result["report"]["test_model"]["n"] == counts["test"]
    assert result["report"]["data_kind"] == "unverified"
    assert "test_platt_calibrated" in result["report"]
    assert (tmp_path / "evaluation" / "test_reliability.png").stat().st_size > 1000
    assert (tmp_path / "evaluation" / "research_experiment.json").is_file()
    assert (tmp_path / "evaluation" / "model_quality.json").is_file()
    predictions = pd.read_csv(tmp_path / "evaluation" / "real_holdout_predictions.csv")
    validate_predictions(predictions)
    assert len(predictions) == 400
    assert "company_response" not in predictions.columns
    saved = json.loads((tmp_path / "evaluation" / "research_experiment.json").read_text())
    assert saved["counts"] == counts


def test_new_model_uses_only_intake_features():
    assert "company_response" not in FEATURES
    assert "timely_response" not in FEATURES
    assert "has_relief" not in FEATURES
    assert "date_received" not in FEATURES


def test_test_labels_do_not_affect_fitted_model_probabilities(tmp_path: Path):
    frame = synthetic_complaints()
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    generate_real_predictions(frame, a)
    splits = assign_temporal_splits(prepare_research_data(frame))
    test_ids = set(splits.loc[splits.split == "test", "complaint_id"])
    frame.loc[frame.complaint_id.isin(test_ids), "has_relief"] = (
        1 - frame.loc[frame.complaint_id.isin(test_ids), "has_relief"]
    )
    generate_real_predictions(frame, b)
    original = pd.read_csv(a).sort_values("complaint_id").reset_index(drop=True)
    modified = pd.read_csv(b).sort_values("complaint_id").reset_index(drop=True)
    np.testing.assert_allclose(original["y_prob"], modified["y_prob"], rtol=0, atol=1e-12)


def test_date_boundaries_not_shared(tmp_path: Path):
    df = synthetic_complaints(400)
    df["date_received"] = np.repeat(pd.date_range("2025-01-01", periods=100, freq="D"), 4)
    csv = tmp_path / "scores.csv"
    generate_real_predictions(df, csv)
    predictions = pd.read_csv(csv)
    assert predictions.groupby("date_received")["split"].nunique().max() == 1
    validate_predictions(predictions)


def test_reject_duplicate_ids():
    frame = synthetic_complaints()
    frame.loc[1, "complaint_id"] = frame.loc[0, "complaint_id"]
    with pytest.raises(ValueError, match="repeated complaint_id"):
        prepare_research_data(frame)


def test_reject_small_fixture(tmp_path: Path):
    with pytest.raises(ValueError, match="at least 160"):
        generate_real_predictions(synthetic_complaints(12), tmp_path / "no.csv")


def test_reject_missing_labels():
    frame = synthetic_complaints()
    frame.loc[0, "has_relief"] = np.nan
    with pytest.raises(ValueError, match="Missing relief labels"):
        prepare_research_data(frame)


def test_reject_non_usable_one_class_period(tmp_path: Path):
    frame = synthetic_complaints()
    frame.loc[frame["date_received"] > "2025-10-01", "has_relief"] = 0
    with pytest.raises(ValueError, match="Both outcomes required"):
        generate_real_predictions(frame, tmp_path / "no.csv")
