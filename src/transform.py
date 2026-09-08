"""Deterministic cleaning and feature engineering."""

from __future__ import annotations

import pandas as pd

CANONICAL_COLUMNS = {
    "Complaint ID": "complaint_id",
    "Date received": "date_received",
    "Product": "product",
    "Issue": "issue",
    "Company": "company",
    "State": "state",
    "Timely response?": "timely_response",
    "Consumer disputed?": "consumer_disputed",
    "Company response to consumer": "company_response",
    "timely": "timely_response",
}


def clean_complaints(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one typed, deduplicated row per complaint.

    The function accepts either CFPB display names or already-normalized sample
    names so the same transformation is testable without a network call.
    """
    df = raw.rename(columns=CANONICAL_COLUMNS).copy()
    required = ["complaint_id", "date_received", "product", "issue", "company"]
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    optional_defaults = {
        "state": "Unknown",
        "timely_response": "Unknown",
        "consumer_disputed": "Unknown",
        "company_response": "Unknown",
    }
    for column, default in optional_defaults.items():
        if column not in df:
            df[column] = default

    df["complaint_id"] = df["complaint_id"].astype(str).str.strip()
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce", utc=True).dt.tz_localize(None)
    for column in ["product", "issue", "company", "state", "timely_response", "consumer_disputed", "company_response"]:
        df[column] = df[column].fillna("Unknown").astype(str).str.strip()

    df = df.dropna(subset=["date_received"])
    df = df[df["complaint_id"].ne("")]
    df = df.drop_duplicates(subset="complaint_id", keep="last")
    df["received_month"] = df["date_received"].dt.to_period("M").dt.to_timestamp()
    binary = {"yes": 1, "no": 0}
    df["is_timely"] = df["timely_response"].str.casefold().map(binary).astype("Int64")
    df["is_disputed"] = df["consumer_disputed"].str.casefold().map(binary).astype("Int64")
    df["has_relief"] = df["company_response"].str.contains("relief", case=False, na=False).astype(int)
    return df.sort_values(["date_received", "complaint_id"]).reset_index(drop=True)


def quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Produce machine-readable quality checks for auditability."""
    checks = [
        ("row_count_positive", len(df) > 0, len(df)),
        ("complaint_id_unique", df["complaint_id"].is_unique, int(df["complaint_id"].duplicated().sum())),
        ("date_received_complete", df["date_received"].notna().all(), int(df["date_received"].isna().sum())),
        ("product_complete", df["product"].ne("Unknown").all(), int(df["product"].eq("Unknown").sum())),
        ("is_timely_binary", df["is_timely"].dropna().isin([0, 1]).all(), int((~df["is_timely"].dropna().isin([0, 1])).sum())),
    ]
    return pd.DataFrame(checks, columns=["check_name", "passed", "observed"])
