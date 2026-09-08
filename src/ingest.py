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


def download_cfpb(limit: int, start_date: str, timeout: int = 60) -> pd.DataFrame:
    """Download unique complaint pages from the official CFPB API.

    The API uses search-after pagination. Each response provides the marker
    needed to retrieve the next page.
    """
    page_size = 25
    page_number = 1
    search_after: str | None = None
    rows: list[dict] = []
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
            params["page"] = page_number
            params["frm"] = (page_number - 1) * page_size
            params["search_after"] = search_after

        for attempt in range(5):
            response = session.get(CFPB_CSV_URL, params=params, timeout=timeout)
            if response.status_code != 429:
                break
            time.sleep(2**attempt)

        response.raise_for_status()
        payload = response.json()
        hits = payload.get("hits", {}).get("hits", [])
        page_rows = [hit["_source"] for hit in hits]
        rows.extend(page_rows)

        if len(page_rows) < requested_size or len(rows) >= limit:
            break

        next_page = page_number + 1
        break_points = payload.get("_meta", {}).get("break_points", {})
        marker = break_points.get(str(next_page))

        if not marker or len(marker) != 2:
            raise RuntimeError(
                f"CFPB API did not provide a pagination marker for page {next_page}"
            )

        search_after = f"{marker[0]}_{marker[1]}"
        page_number = next_page
        time.sleep(0.4)

    return pd.DataFrame(rows[:limit])