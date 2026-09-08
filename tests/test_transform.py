import pandas as pd
import pytest

from src.transform import clean_complaints, quality_report


def test_clean_deduplicates_and_builds_features():
    raw = pd.DataFrame({
        "complaint_id": ["1", "1", "2"],
        "date_received": ["2024-01-01", "2024-01-02", "2024-02-01"],
        "product": ["Card", "Card", "Mortgage"],
        "issue": ["Fee", "Fee", "Escrow"],
        "company": ["A", "A", "B"],
        "timely_response": ["Yes", "No", "Yes"],
        "consumer_disputed": ["No", "Yes", "No"],
        "company_response": ["Closed", "Relief", "Closed"],
    })
    clean = clean_complaints(raw)
    assert len(clean) == 2
    assert clean.loc[clean["complaint_id"] == "1", "is_timely"].item() == 0
    assert clean["has_relief"].sum() == 1
    assert quality_report(clean)["passed"].all()


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="Missing required columns"):
        clean_complaints(pd.DataFrame({"complaint_id": ["1"]}))

