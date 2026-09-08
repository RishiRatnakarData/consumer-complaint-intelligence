"""Tests for time-stratified CFPB sampling."""

import pandas as pd

from src import sampling


def test_weekly_sample_allocates_rows_across_windows(
    monkeypatch,
) -> None:
    calls: list[tuple[int, str, str]] = []
    next_id = 0

    def fake_download(
        limit: int,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        nonlocal next_id
        calls.append((limit, start_date, end_date))
        frame = pd.DataFrame(
            {
                "complaint_id": [
                    str(value)
                    for value in range(next_id, next_id + limit)
                ]
            }
        )
        next_id += limit
        return frame

    monkeypatch.setattr(
        sampling,
        "download_cfpb",
        fake_download,
    )

    result = sampling.download_weekly_stratified_sample(
        limit=5,
        start_date="2025-01-01",
        end_date="2025-01-14",
    )

    assert len(result) == 5
    assert result["complaint_id"].nunique() == 5
    assert calls == [
        (3, "2025-01-01", "2025-01-07"),
        (2, "2025-01-08", "2025-01-14"),
    ]