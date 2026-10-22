import pandas as pd
import pytest
from cfpb_quality.validation import validate_predictions


def valid():
    return pd.DataFrame({"complaint_id": [1, 2, 3, 4],
                         "date_received": ["2025-01-01", "2025-01-02", "2025-02-01", "2025-03-01"],
                         "split": ["train", "train", "validation", "test"],
                         "y_true": [0, 1, 0, 1], "y_prob": [0.2, 0.7, 0.2, 0.8]})


def test_accepts_proper_chronology():
    assert len(validate_predictions(valid())) == 4


@pytest.mark.parametrize("field", ["y_true", "y_prob", "split", "date_received"])
def test_missing_required_column_fails(field):
    with pytest.raises(ValueError):
        validate_predictions(valid().drop(columns=field))


def test_future_train_date_fails():
    data = valid()
    data.loc[0, "date_received"] = "2025-04-01"
    with pytest.raises(ValueError, match="Chronological overlap"):
        validate_predictions(data)


def test_same_day_between_splits_fails():
    data = valid()
    data.loc[2, "date_received"] = "2025-01-02"
    with pytest.raises(ValueError, match="Chronological overlap"):
        validate_predictions(data)


def test_duplicate_ids_fail():
    data = valid()
    data.loc[3, "complaint_id"] = 1
    with pytest.raises(ValueError, match="Duplicate"):
        validate_predictions(data)


@pytest.mark.parametrize("bad", [-0.01, 1.1, float('nan'), float('inf')])
def test_invalid_probability_fails(bad):
    data = valid()
    data.loc[0, "y_prob"] = bad
    with pytest.raises(ValueError):
        validate_predictions(data)


def test_nonbinary_target_fails():
    data = valid()
    data["y_true"] = data["y_true"].astype(float)
    data.loc[0, "y_true"] = 0.5
    with pytest.raises(ValueError):
        validate_predictions(data)


def test_missing_train_split_fails():
    data = valid()
    data["split"] = "test"
    with pytest.raises(ValueError, match="train"):
        validate_predictions(data)


def test_null_id_fails():
    data = valid()
    data.loc[1, "complaint_id"] = None
    with pytest.raises(ValueError, match="Missing complaint_id"):
        validate_predictions(data)
