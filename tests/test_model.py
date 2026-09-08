"""Tests for the relief-outcome model."""

from pathlib import Path

import pandas as pd

from src.model import fit_relief_model


def make_model_data(rows: int = 80) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "complaint_id": [str(index) for index in range(rows)],
            "date_received": pd.date_range(
                "2025-01-01",
                periods=rows,
                freq="D",
            ),
            "company": [
                "Company A" if index % 2 else "Company B"
                for index in range(rows)
            ],
            "product": [
                "Credit card" if index % 3 else "Mortgage"
                for index in range(rows)
            ],
            "sub_product": [
                "General purpose card"
                if index % 4
                else None
                for index in range(rows)
            ],
            "issue": [
                "Incorrect information"
                if index % 2
                else "Managing an account"
                for index in range(rows)
            ],
            "state": [
                "VA" if index % 2 else "MD"
                for index in range(rows)
            ],
            "submitted_via": [
                "Web" if index % 3 else "Phone"
                for index in range(rows)
            ],
            "has_narrative": [
                bool(index % 2)
                for index in range(rows)
            ],
            "has_relief": [
                int(index % 3 == 0)
                for index in range(rows)
            ],
        }
    )


def test_relief_model_reports_comparative_metrics(
    tmp_path: Path,
) -> None:
    metrics = fit_relief_model(
        make_model_data(),
        tmp_path / "metrics.json",
    )

    assert metrics["status"] == "completed"
    assert metrics["target"] == "has_relief"
    assert metrics["train_rows"] == 60
    assert metrics["test_rows"] == 20
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["balanced_accuracy"] <= 1.0
    assert sum(metrics["confusion_matrix"].values()) == 20


def test_relief_model_skips_single_class(
    tmp_path: Path,
) -> None:
    data = make_model_data(40)
    data["has_relief"] = 0

    metrics = fit_relief_model(
        data,
        tmp_path / "metrics.json",
    )

    assert metrics["status"] == "skipped"