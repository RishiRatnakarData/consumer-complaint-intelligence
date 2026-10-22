"""Binary classification quality measures with defined edge-case handling."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, log_loss, precision_score,
                             recall_score, roc_auc_score)


def reliability_bins(y_true, y_prob, bins: int = 10) -> list[dict]:
    y, p = np.asarray(y_true, dtype=int), np.asarray(y_prob, dtype=float)
    assignment = np.minimum((p * bins).astype(int), bins - 1)
    result = []
    for i in range(bins):
        idx = assignment == i
        result.append({"lower": i / bins, "upper": (i + 1) / bins,
                       "count": int(idx.sum()),
                       "predicted": float(p[idx].mean()) if idx.any() else None,
                       "observed": float(y[idx].mean()) if idx.any() else None})
    return result


def evaluate(y_true, y_prob, threshold: float = 0.5, bins: int = 10) -> dict:
    y, p = np.asarray(y_true, dtype=int), np.asarray(y_prob, dtype=float)
    if len(y) == 0:
        raise ValueError("Cannot evaluate an empty holdout")
    prediction = (p >= threshold).astype(int)
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, prediction, labels=[0, 1]).ravel())
    rel = reliability_bins(y, p, bins)
    ece = sum(x["count"] * abs(x["predicted"] - x["observed"]) for x in rel if x["count"]) / len(y)
    both = len(set(y.tolist())) == 2
    return {"n": len(y), "prevalence": float(y.mean()), "threshold": float(threshold),
            "roc_auc": float(roc_auc_score(y, p)) if both else None,
            "average_precision": float(average_precision_score(y, p)) if both else None,
            "brier_score": float(brier_score_loss(y, p)),
            "log_loss": float(log_loss(y, np.clip(p, 1e-12, 1 - 1e-12), labels=[0, 1])),
            "ece_10bins": float(ece),
            "accuracy": float(accuracy_score(y, prediction)),
            "precision": float(precision_score(y, prediction, zero_division=0)),
            "recall": float(recall_score(y, prediction, zero_division=0)),
            "f1": float(f1_score(y, prediction, zero_division=0)),
            "review_rate": float(prediction.mean()),
            "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
            "reliability_bins": rel}


def select_threshold_on_validation(y_true, y_prob, minimum_recall: float = 0.8):
    """Highest threshold meeting a predeclared recall floor on validation only."""
    y, p = np.asarray(y_true, dtype=int), np.asarray(y_prob, dtype=float)
    if (y == 1).sum() == 0:
        raise ValueError("Validation has no positive outcomes; cannot set recall floor")
    for threshold in np.linspace(0.95, 0.05, 19):
        recall = recall_score(y, p >= threshold, zero_division=0)
        if recall >= minimum_recall:
            return float(round(threshold, 2)), float(recall)
    raise ValueError("No threshold on the predeclared grid meets the validation recall floor")
