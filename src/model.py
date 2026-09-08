"""Interpretable modeling demonstration with leakage-aware features."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def fit_timeliness_model(df: pd.DataFrame, output_path: Path) -> dict[str, float | int | str]:
    """Predict timely response using only fields known at complaint receipt.

    This is an explanatory portfolio model, not a causal or production claim.
    A chronological holdout avoids learning from future periods.
    """
    model_df = df.dropna(subset=["is_timely"]).copy()
    model_df["is_timely"] = model_df["is_timely"].astype(int)
    if len(model_df) < 10 or model_df["is_timely"].nunique() < 2:
        metrics = {"status": "skipped", "reason": "Need >=10 labeled rows and both target classes", "rows": len(model_df)}
    else:
        ordered = model_df.sort_values("date_received").copy()
        split = max(1, int(len(ordered) * 0.75))
        train, test = ordered.iloc[:split], ordered.iloc[split:]
        features = ["product", "state"]
        pipeline = Pipeline([
            ("encode", ColumnTransformer([("category", OneHotEncoder(handle_unknown="ignore"), features)])),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ])
        pipeline.fit(train[features], train["is_timely"])
        probability = pipeline.predict_proba(test[features])[:, 1]
        prediction = (probability >= 0.5).astype(int)
        metrics = {
            "status": "completed",
            "train_rows": len(train),
            "test_rows": len(test),
            "accuracy": round(float(accuracy_score(test["is_timely"], prediction)), 4),
            "roc_auc": round(float(roc_auc_score(test["is_timely"], probability)), 4) if test["is_timely"].nunique() == 2 else "not_defined",
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics
