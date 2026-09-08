"""CFPB download with explicit sample fallback."""

from __future__ import annotations

from pathlib import Path
import time

import pandas as pd
import requests

CFPB_CSV_URL = (
    "https://www.consumerfinance.gov/data-research/"
    "consumer-complaints/search/api/v1/"
)


def load_sample(root: Path) -> pd.DataFrame:
    return pd.read_csv(root / "data" / "sample" / "complaints_sample.csv")


def download_cfpb(limit: int, start_date: str, timeout: int = 30) -> pd.DataFrame:
    """Download unique complaint pages from the official CFPB API.

    Sequential pages use the sort cursor from the final hit of each response.
    Transient server errors, rate limits, and connection failures are retried.
    """
    page_size = 100
    rows: list[dict] = []
    seen_ids: set[str] = set()
    search_after: str | None = None
    session = requests.Session()

    while len(rows) < limit:
        requested_size = min(page_size, limit - len(rows))
        params: dict[str, str | int] = {
            "date_received_min": start_date,
            "size": requested_size,
            "sort": "created_date_desc",
            "no_aggs": "true",
        }

        if search_after is not None:
            params["search_after"] = search_after

        for attempt in range(5):
            try:
                response = session.get(
                    CFPB_CSV_URL,
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
        hits = payload.get("hits", {}).get("hits", [])
        page_rows = [hit["_source"] for hit in hits]

        page_ids = {
            str(row["complaint_id"])
            for row in page_rows
            if row.get("complaint_id") is not None
        }
        repeated_ids = page_ids.intersection(seen_ids)

        if repeated_ids:
            raise RuntimeError(
                "CFPB API returned duplicate records across sequential pages"
            )

        seen_ids.update(page_ids)
        rows.extend(page_rows)

        print(
            f"Downloaded {min(len(rows), limit):,}/{limit:,} complaints",
            flush=True,
        )

        if len(page_rows) < requested_size or len(rows) >= limit:
            break

        marker = hits[-1].get("sort")
        if not marker or len(marker) != 2:
            raise RuntimeError(
                "CFPB API did not provide a cursor for the next page"
            )

        search_after = f"{marker[0]}_{marker[1]}"
        time.sleep(0.2)

    return pd.DataFrame(rows[:limit])