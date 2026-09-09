import pandas as pd
import pytest

from src.transform import clean_complaints, quality_report


def test_clean_deduplicates_and_builds_features():
    raw = pd.DataFrame({
        "complaint_id": ["1", "1", "2"],
        "date_received": [
            "2024-01-01",
            "2024-01-02",
            "2024-02-01",
        ],
        "product": ["Card", "Card", "Mortgage"],
        "issue": ["Fee", "Fee", "Escrow"],
        "company": ["A", "A", "B"],
        "timely_response": ["Yes", "No", "Yes"],
        "consumer_disputed": ["No", "Yes", "No"],
        "company_response": ["Closed", "Relief", "Closed"],
    })

    clean = clean_complaints(raw)

    assert len(clean) == 2
    assert (
        clean.loc[
            clean["complaint_id"] == "1",
            "is_timely",
        ].item()
        == 0
    )
    assert clean["has_relief"].sum() == 1
    assert quality_report(clean)["passed"].all()


def test_optional_model_fields_receive_safe_defaults():
    raw = pd.DataFrame({
        "complaint_id": ["1"],
        "date_received": ["2024-01-01"],
        "product": ["Card"],
        "issue": ["Fee"],
        "company": ["A"],
    })

    clean = clean_complaints(raw)

    assert clean.loc[0, "sub_product"] == "Unknown"
    assert clean.loc[0, "submitted_via"] == "Unknown"
    assert clean.loc[0, "complaint_what_happened"] == ""
    assert clean.loc[0, "has_narrative"] == 0


def test_narrative_feature_detects_nonempty_text():
    raw = pd.DataFrame({
        "complaint_id": ["1", "2"],
        "date_received": ["2024-01-01", "2024-01-02"],
        "product": ["Card", "Card"],
        "issue": ["Fee", "Fee"],
        "company": ["A", "A"],
        "complaint_what_happened": ["", "Unexpected charge"],
    })

    clean = clean_complaints(raw)

    assert clean["has_narrative"].tolist() == [0, 1]


def test_missing_required_column_raises():
    with pytest.raises(
        ValueError,
        match="Missing required columns",
    ):
        clean_complaints(pd.DataFrame({"complaint_id": ["1"]}))