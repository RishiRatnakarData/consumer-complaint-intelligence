import json
import pandas as pd
import pytest
from cfpb_quality.report import create_report
from scripts.make_demo_predictions import generate


def test_demo_report_end_to_end(tmp_path):
    csv = tmp_path / "demo.csv"
    generate(csv)
    result = create_report(csv, tmp_path / "artifacts", min_group_n=30)
    assert result["test_model"]["n"] == 240
    assert len(result["input_sha256"]) == 64
    assert result["date_ranges"]["train"]["end"] < result["date_ranges"]["test"]["start"]
    assert "test_platt_calibrated" in result
    assert (tmp_path / "artifacts/model_quality.json").exists()
    assert (tmp_path / "artifacts/test_reliability.png").stat().st_size > 1000
    saved = json.loads((tmp_path / "artifacts/model_quality.json").read_text())
    assert saved["test_model"]["brier_score"] >= 0
    assert "product" in saved["subgroups"]


def test_no_validation_does_not_tune_test(tmp_path):
    csv = tmp_path / "demo.csv"
    generate(csv)
    frame = pd.read_csv(csv)
    frame = frame.loc[frame["split"] != "validation"]
    frame.to_csv(csv, index=False)
    result = create_report(csv, tmp_path / "out")
    assert result["threshold_source"] == "prespecified 0.50"
    assert "test_platt_calibrated" not in result


def test_test_labels_cannot_move_into_training(tmp_path):
    csv = tmp_path / "demo.csv"
    generate(csv)
    frame = pd.read_csv(csv)
    frame.loc[frame["split"] == "test", "date_received"] = "2025-01-01"
    frame.to_csv(csv, index=False)
    with pytest.raises(ValueError, match="Chronological overlap"):
        create_report(csv, tmp_path / "out")


def test_subgroups_suppressed_when_small(tmp_path):
    csv = tmp_path / "demo.csv"
    generate(csv)
    result = create_report(csv, tmp_path / "out", min_group_n=500)
    assert result["subgroups"]["product"] == []
