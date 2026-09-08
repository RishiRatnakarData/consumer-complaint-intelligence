"""Time-stratified sampling for CFPB complaint details."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.ingest import download_cfpb


def download_weekly_stratified_sample(
    limit: int,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Distribute a detail-row limit across weekly date windows."""
    if limit < 1:
        raise ValueError("limit must be at least 1")

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    if end < start:
        raise ValueError("end_date must not be before start_date")

    windows: list[tuple[date, date]] = []
    window_start = start

    while window_start <= end:
        window_end = min(
            window_start + timedelta(days=6),
            end,
        )
        windows.append((window_start, window_end))
        window_start = window_end + timedelta(days=1)

    base_rows, remainder = divmod(limit, len(windows))
    frames: list[pd.DataFrame] = []

    for index, (window_start, window_end) in enumerate(windows):
        window_limit = base_rows + (1 if index < remainder else 0)

        if window_limit == 0:
            continue

        print(
            "Sampling "
            f"{window_start.isoformat()} through "
            f"{window_end.isoformat()}: "
            f"{window_limit:,} rows",
            flush=True,
        )

        frame = download_cfpb(
            limit=window_limit,
            start_date=window_start.isoformat(),
            end_date=window_end.isoformat(),
        )
        frames.append(frame)

    if not frames:
        raise RuntimeError("No CFPB sampling windows were created")

    sample = pd.concat(frames, ignore_index=True)
    sample = sample.drop_duplicates(
        subset=["complaint_id"],
        keep="first",
    )

    if len(sample) < limit:
        raise RuntimeError(
            f"Requested {limit:,} unique complaints but received "
            f"{len(sample):,}"
        )

    return sample.iloc[:limit].reset_index(drop=True)