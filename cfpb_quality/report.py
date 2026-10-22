"""Offline, no-PII diagnostic reporting. No model retraining or decision automation."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from .metrics import evaluate, select_threshold_on_validation
from .validation import validate_predictions


def _plot_calibration(reliability, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], linestyle="--", linewidth=1, label="Perfect calibration")
    observed = [(r["predicted"], r["observed"], r["count"]) for r in reliability if r["count"]]
    ax.scatter([r[0] for r in observed], [r[1] for r in observed],
               s=[max(20, r[2] * 0.6) for r in observed], label="Test bins")
    ax.set(xlabel="Mean predicted relief probability", ylabel="Observed relief frequency",
           title="Test-set reliability (equal-width bins)", xlim=(0, 1), ylim=(0, 1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _group_diagnostics(test: pd.DataFrame, field: str, min_n: int, threshold: float) -> list[dict]:
    if field not in test:
        return []
    out = []
    # Aggregate metrics only; suppress small groups and missing groups.
    for name, subset in test.dropna(subset=[field]).groupby(field, sort=True):
        if len(subset) < min_n:
            continue
        m = evaluate(subset["y_true"], subset["y_prob"], threshold)
        out.append({"group": str(name), "n": m["n"], "observed_relief": m["prevalence"],
                    "brier_score": m["brier_score"], "recall": m["recall"],
                    "review_rate": m["review_rate"], "roc_auc": m["roc_auc"]})
    return out


def _platt_predict(validation: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Fit sigmoid mapping on validation ONLY, apply to untouched test data."""
    eps = 1e-6
    def logit(series):
        p = np.clip(series.to_numpy(dtype=float), eps, 1 - eps)
        return np.log(p / (1 - p)).reshape(-1, 1)
    if validation["y_true"].nunique() < 2 or len(validation) < 30:
        raise ValueError("Calibrator requires >=30 validation rows and both outcome classes")
    calibrator = LogisticRegression(solver="lbfgs", max_iter=1000)
    calibrator.fit(logit(validation["y_prob"]), validation["y_true"])
    return calibrator.predict_proba(logit(test["y_prob"]))[:, 1]


def create_report(csv_path: str | Path, output_dir: str | Path, *,
                  min_group_n: int = 50, minimum_recall: float = 0.8,
                  calibrate: bool = True, data_kind: str = "unverified") -> dict:
    if data_kind not in {"synthetic", "cfpb_sample", "unverified"}:
        raise ValueError("data_kind must be synthetic, cfpb_sample or unverified")
    if min_group_n < 1 or not (0 < minimum_recall <= 1):
        raise ValueError("min_group_n must be positive and minimum_recall in (0, 1]")
    csv_path = Path(csv_path)
    input_sha256 = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    df = validate_predictions(pd.read_csv(csv_path))
    train = df.loc[df["split"] == "train"]
    test = df.loc[df["split"] == "test"]
    validation = df.loc[df["split"] == "validation"]
    notes = ["Scores are evaluated on the supplied test period; they are NOT newly trained models.",
             "All group metrics are descriptive and lack adjustments for complaint mix or exposure.",
             "This evaluation uses the sampled detail data, not the full population aggregate."]
    threshold, selected_recall = 0.5, None
    if len(validation):
        try:
            threshold, selected_recall = select_threshold_on_validation(
                validation["y_true"], validation["y_prob"], minimum_recall)
        except ValueError as err:
            notes.append(f"Validation threshold selection unavailable: {err}; predeclared 0.50 used")
    else:
        notes.append("No validation set supplied: threshold is fixed at 0.50, not tuned on test")
    train_prevalence = float(train["y_true"].mean())
    baseline_scores = np.full(len(test), train_prevalence, dtype=float)
    result = {
        "scope": "Supplied row-level predictions; NOT full-population complaint aggregates",
        "data_kind": data_kind,
        "input_sha256": input_sha256,
        "date_ranges": {key: {"start": subset["date_received"].min().date().isoformat(),
                              "end": subset["date_received"].max().date().isoformat()}
                        for key, subset in df.groupby("split")},
        "split_counts": {str(key): int(value) for key, value in df["split"].value_counts().items()},
        "train_prevalence_baseline": train_prevalence,
        "threshold_source": "validation" if selected_recall is not None else "prespecified 0.50",
        "validation_recall_at_selected_threshold": selected_recall,
        "test_model": evaluate(test["y_true"], test["y_prob"], threshold),
        "test_constant_baseline": evaluate(test["y_true"], baseline_scores, 0.5),
        "subgroups": {field: _group_diagnostics(test, field, min_group_n, threshold)
                      for field in ("product", "company")},
        "notes": notes}
    notes.append("Baseline classification statistics use cutoff 0.50, not the validation-selected model cutoff; compare probability scores primarily")
    if calibrate and len(validation):
        try:
            calibrated = _platt_predict(validation, test)
            result["test_platt_calibrated"] = evaluate(test["y_true"], calibrated, 0.5)
            result["notes"].append("Platt calibration fitted on validation and compared on test using a 0.50 probability classification cutoff; validation-selected raw-score threshold applies ONLY to test_model")
        except ValueError as err:
            notes.append(f"Calibration skipped: {err}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_quality.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    _plot_calibration(result["test_model"]["reliability_bins"], out / "test_reliability.png")
    return result
