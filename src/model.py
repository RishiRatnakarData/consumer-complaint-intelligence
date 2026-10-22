"""Interpretable, leakage-aware relief-outcome model."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


def fit_relief_model(
    df: pd.DataFrame,
    output_path: Path,
) -> dict[str, object]:
    """Predict relief using fields available near complaint intake.

    This is a prioritization model, not a causal model or an
    automated decision system. A chronological holdout limits future leakage.
    """
    categorical_features = [
        "company",
        "product",
        "sub_product",
        "issue",
        "state",
        "submitted_via",
    ]
    # The narrative field can be absent from newer CFPB extracts. Select
    # features using only training-period values, never test outcomes.
    candidate_binary_features = ["has_narrative"]
    target = "has_relief"

    model_df = df.dropna(
        subset=[target, "date_received", "complaint_id"]
    ).copy()
    model_df[target] = model_df[target].astype(int)

    for column in categorical_features:
        model_df[column] = (
            model_df[column]
            .fillna("Unknown")
            .astype(str)
        )

    model_df["has_narrative"] = (
        model_df["has_narrative"]
        .fillna(False)
        .astype(int)
    )

    if len(model_df) < 40 or model_df[target].nunique() < 2:
        metrics: dict[str, object] = {
            "status": "skipped",
            "reason": "Need at least 40 labeled rows and both target classes",
            "rows": len(model_df),
        }
    else:
        ordered = model_df.sort_values(
            ["date_received", "complaint_id"]
        ).copy()
        split = int(len(ordered) * 0.75)
        train = ordered.iloc[:split]
        test = ordered.iloc[split:]

        if (
            train[target].nunique() < 2
            or test[target].nunique() < 2
        ):
            metrics = {
                "status": "skipped",
                "reason": (
                    "Both chronological partitions need both target classes"
                ),
                "rows": len(model_df),
            }
        else:
            binary_features = [
                field for field in candidate_binary_features
                if train[field].nunique(dropna=False) > 1
            ]
            features = categorical_features + binary_features
            excluded_features = sorted(set(candidate_binary_features) - set(binary_features))
            feature_transformers = [
                (
                    "category",
                    OneHotEncoder(handle_unknown="ignore", min_frequency=5),
                    categorical_features,
                )
            ]
            if binary_features:
                feature_transformers.append(("binary", "passthrough", binary_features))
            pipeline = Pipeline(
                [
                    (
                        "encode",
                        ColumnTransformer(
                            feature_transformers
                        ),
                    ),
                    (
                        "model",
                        LogisticRegression(
                            max_iter=1000,
                            class_weight="balanced",
                        ),
                    ),
                ]
            )
            pipeline.fit(train[features], train[target])

            probability = pipeline.predict_proba(
                test[features]
            )[:, 1]
            prediction = (probability >= 0.5).astype(int)
            tn, fp, fn, tp = confusion_matrix(
                test[target],
                prediction,
                labels=[0, 1],
            ).ravel()

            baseline_accuracy = float(
                test[target].value_counts(
                    normalize=True
                ).max()
            )

            metrics = {
                "status": "completed",
                "target": target,
                "features": features,
                "excluded_features": excluded_features,
                "narrative_feature_audit": {
                    "train_positive_rows": int(train["has_narrative"].sum()),
                    "sample_positive_rows": int(model_df["has_narrative"].sum()),
                    "train_unique_values": int(train["has_narrative"].nunique()),
                    "interpretation": (
                        "Constant in training; excluded from modeling; "
                        "absence of source text does not establish no narrative was submitted"
                        if "has_narrative" in excluded_features
                        else "Varies in training and was retained"
                    ),
                },
                "train_rows": len(train),
                "test_rows": len(test),
                "overall_relief_rate": round(
                    float(model_df[target].mean()),
                    4,
                ),
                "baseline_accuracy": round(
                    baseline_accuracy,
                    4,
                ),
                "accuracy": round(
                    float(
                        accuracy_score(
                            test[target],
                            prediction,
                        )
                    ),
                    4,
                ),
                "balanced_accuracy": round(
                    float(
                        balanced_accuracy_score(
                            test[target],
                            prediction,
                        )
                    ),
                    4,
                ),
                "precision": round(
                    float(
                        precision_score(
                            test[target],
                            prediction,
                            zero_division=0,
                        )
                    ),
                    4,
                ),
                "recall": round(
                    float(
                        recall_score(
                            test[target],
                            prediction,
                            zero_division=0,
                        )
                    ),
                    4,
                ),
                "f1": round(
                    float(
                        f1_score(
                            test[target],
                            prediction,
                            zero_division=0,
                        )
                    ),
                    4,
                ),
                "roc_auc": round(
                    float(
                        roc_auc_score(
                            test[target],
                            probability,
                        )
                    ),
                    4,
                ),
                "average_precision": round(
                    float(
                        average_precision_score(
                            test[target],
                            probability,
                        )
                    ),
                    4,
                ),
                "confusion_matrix": {
                    "true_negative": int(tn),
                    "false_positive": int(fp),
                    "false_negative": int(fn),
                    "true_positive": int(tp),
                },
            }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return metrics
