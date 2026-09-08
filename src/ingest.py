"""CFPB download with explicit sample fallback."""

from __future__ import annotations

from pathlib import Path
import time

import pandas as pd
import requests

CFPB_CSV_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"


def load_sample(root: Path) -> pd.DataFrame:
    return pd.read_csv(root / "data" / "sample" / "complaints_sample.csv")


def download_cfpb(limit: int, start_date: str, timeout: int = 60) -> pd.DataFrame:
    """Page through the official JSON API without downloading the full export.

    The deployed API currently accepts small pages, so a polite pause and 429
    retry are used. Large portfolio runs can take several minutes.
    """
    page_size = 25
    rows: list[dict] = []
    session = requests.Session()
    while len(rows) < limit:
        params = {
            "date_received_min": start_date,
            "size": min(page_size, limit - len(rows)),
            "sort": "created_date_desc",
            "no_aggs": "true",
        }
        if rows:
            params["frm"] = len(rows)
        for attempt in range(5):
            response = session.get(CFPB_CSV_URL, params=params, timeout=timeout)
            if response.status_code != 429:
                break
            time.sleep(2 ** attempt)
        response.raise_for_status()
        hits = response.json().get("hits", {}).get("hits", [])
        page = [hit["_source"] for hit in hits]
        rows.extend(page)
        if len(page) < params["size"]:
            break
        time.sleep(0.4)
    return pd.DataFrame(rows[:limit])
