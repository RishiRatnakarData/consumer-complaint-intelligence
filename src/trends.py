"""Retrieve full-population monthly complaint counts from the CFPB."""

from __future__ import annotations

import time

import pandas as pd
import requests

CFPB_TRENDS_URL = (
    "https://www.consumerfinance.gov/data-research/"
    "consumer-complaints/search/api/v1/trends"
)


def download_monthly_counts(
    start_date: str,
    end_date: str,
    timeout: int = 30,
) -> pd.DataFrame:
    """Download official monthly complaint totals for a date range."""
    params = {
        "lens": "overview",
        "trend_interval": "month",
        "date_received_min": start_date,
        "date_received_max": end_date,
    }
    session = requests.Session()

    for attempt in range(5):
        try:
            response = session.get(
                CFPB_TRENDS_URL,
                params=params,
                timeout=timeout,
            )

            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 4:
                    response.raise_for_status()
                time.sleep(2**attempt)
                continue

            response.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 4:
                raise
            time.sleep(2**attempt)

    payload = response.json()
    buckets = (
        payload.get("aggregations", {})
        .get("dateRangeArea", {})
        .get("dateRangeArea", {})
        .get("buckets", [])
    )

    monthly = pd.DataFrame(
        [
            {
                "received_month": bucket["key_as_string"][:10],
                "official_complaint_count": int(bucket["doc_count"]),
            }
            for bucket in buckets
        ]
    )

    if monthly.empty:
        raise RuntimeError("CFPB trends API returned no monthly counts")

    monthly["received_month"] = pd.to_datetime(
        monthly["received_month"]
    )
    monthly = monthly.sort_values("received_month").reset_index(drop=True)

    if monthly["received_month"].duplicated().any():
        raise RuntimeError("CFPB trends API returned duplicate months")

    if (monthly["official_complaint_count"] < 0).any():
        raise RuntimeError("CFPB trends API returned a negative count")

    return monthly