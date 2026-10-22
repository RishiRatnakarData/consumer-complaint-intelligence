"""Input contracts and temporal leakage defenses."""
from __future__ import annotations

import numpy as np
import pandas as pd

REQUIRED = {"date_received", "split", "y_true", "y_prob"}
ALLOWED = {"train", "validation", "test"}


def validate_predictions(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = frame.copy()
    df["split"] = df["split"].astype(str).str.strip().str.lower()
    bad_splits = sorted(set(df["split"]) - ALLOWED)
    if bad_splits:
        raise ValueError(f"Unknown split values: {bad_splits}")
    for split in ("train", "test"):
        if not (df["split"] == split).any():
            raise ValueError(f"Required split '{split}' is empty")
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce", utc=True)
    if df["date_received"].isna().any():
        raise ValueError("Invalid or missing date_received")
    if df[["y_true", "y_prob"]].isna().any().any():
        raise ValueError("Null target or predicted probability")
    # Avoid coercing 0.5 or 'unknown' into an integer silently.
    y = pd.to_numeric(df["y_true"], errors="coerce")
    if y.isna().any() or not y.isin([0, 1]).all():
        raise ValueError("y_true must be binary 0/1")
    df["y_true"] = y.astype(int)
    p = pd.to_numeric(df["y_prob"], errors="coerce")
    if p.isna().any() or not np.isfinite(p.to_numpy()).all() or not p.between(0, 1).all():
        raise ValueError("y_prob must be finite and between 0 and 1")
    df["y_prob"] = p.astype(float)
    if "complaint_id" in df:
        if df["complaint_id"].isna().any():
            raise ValueError("Missing complaint_id; cannot validate unique examples")
        if df["complaint_id"].duplicated().any():
            raise ValueError("Duplicate complaint_id across splits; potential leakage")
    sequence = [s for s in ("train", "validation", "test") if (df["split"] == s).any()]
    for left, right in zip(sequence, sequence[1:]):
        a = df.loc[df["split"] == left, "date_received"].max()
        b = df.loc[df["split"] == right, "date_received"].min()
        if a >= b:
            raise ValueError(f"Chronological overlap: {left} max {a.date()} >= {right} min {b.date()}")
    return df
