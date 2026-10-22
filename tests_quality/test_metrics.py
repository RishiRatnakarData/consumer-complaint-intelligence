import numpy as np
import pytest
from cfpb_quality.metrics import evaluate, select_threshold_on_validation


def test_perfect_model():
    m = evaluate([0, 0, 1, 1], [0.0, 0.1, 0.9, 1.0])
    assert m["roc_auc"] == 1
    assert m["f1"] == 1
    assert m["brier_score"] < 0.01
    assert m["confusion"] == {"tn": 2, "fp": 0, "fn": 0, "tp": 2}


def test_constant_prediction_brier():
    m = evaluate([0, 1], [0.5, 0.5])
    assert m["brier_score"] == pytest.approx(0.25)
    assert m["roc_auc"] == pytest.approx(0.5)


def test_single_class_does_not_invent_auc():
    m = evaluate([0, 0, 0], [0.2, 0.2, 0.2])
    assert m["roc_auc"] is None
    assert m["average_precision"] is None


def test_threshold_selection_requires_recall_floor():
    y = np.array([0, 0, 1, 1, 1])
    p = np.array([0.1, 0.4, 0.45, 0.7, 0.9])
    selected, r = select_threshold_on_validation(y, p, minimum_recall=2/3)
    assert selected == pytest.approx(0.7)
    assert r == pytest.approx(2/3)


def test_threshold_selection_no_positives_fails():
    with pytest.raises(ValueError):
        select_threshold_on_validation([0, 0], [0.2, 0.3])
