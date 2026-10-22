"""Regression tests for optional legacy-trends failure and processed-data reuse."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src import pipeline, trends
from src.transform import clean_complaints


class HtmlResponse:
    status_code = 200
    headers = {"Content-Type": "text/html"}

    def raise_for_status(self):
        return None

    def json(self):
        raise ValueError("Expecting value")


class HtmlSession:
    def get(self, *args, **kwargs):
        return HtmlResponse()


def test_legacy_trends_nonjson_explains_issue(monkeypatch):
    monkeypatch.setattr(trends.requests, "Session", HtmlSession)
    with pytest.raises(trends.CFPBTrendsUnavailable, match="did not return JSON"):
        trends.download_monthly_counts("2025-01-01", "2025-12-31")


def setup_processed(tmp_path: Path, monkeypatch):
    fixture = pd.read_csv(
        Path(__file__).resolve().parents[1] / "data/sample/complaints_sample.csv"
    )
    df = clean_complaints(fixture)
    src = tmp_path / "data/processed"
    src.mkdir(parents=True)
    (src / "complaints.parquet").write_bytes(b"placeholder unit test file")
    monkeypatch.setattr(pipeline.pd, "read_parquet", lambda path: df.copy())
    monkeypatch.setattr(pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pipeline, "build_database", lambda *args: {})

    def fake_fit(*args):
        Path(args[1]).write_text('{"status":"mock"}', encoding="utf-8")
        return {"status": "mock"}

    monkeypatch.setattr(pipeline, "fit_relief_model", fake_fit)
    return df


def test_reuse_processed_skips_network_and_preserves_parquet(tmp_path, monkeypatch):
    df = setup_processed(tmp_path, monkeypatch)
    parquet = tmp_path / "data/processed/complaints.parquet"
    before = parquet.read_bytes()
    monkeypatch.setattr(pipeline, "download_weekly_stratified_sample", lambda *a: pytest.fail("download called"))
    monkeypatch.setattr(pipeline, "download_monthly_counts", lambda *a: pytest.fail("trends called"))
    pipeline.run(False, 5000, "2024-01-01", "2024-12-31", reuse_processed=True,
                 skip_official_counts=True)
    summary = json.loads((tmp_path / "artifacts/run_summary.json").read_text())
    assert summary["detail_sample_rows"] == len(df)
    assert summary["official_counts_status"] == "skipped"
    assert summary["official_period_complaints"] is None
    assert summary["processed_data_reused"] is True
    assert parquet.read_bytes() == before


def test_trends_unavailable_does_not_fabricate_population(tmp_path, monkeypatch):
    setup_processed(tmp_path, monkeypatch)
    old = tmp_path / "artifacts/official_monthly_counts.csv"
    old.parent.mkdir(parents=True)
    old.write_text("received_month,official_complaint_count\n2025-01-01,9999\n", encoding="utf-8")
    monkeypatch.setattr(pipeline, "download_monthly_counts", lambda *a: (_ for _ in ()).throw(
        trends.CFPBTrendsUnavailable("Old endpoint returned HTML")))
    pipeline.run(False, 5000, "2024-01-01", "2024-12-31", reuse_processed=True)
    summary = json.loads((tmp_path / "artifacts/run_summary.json").read_text())
    assert summary["official_counts_status"] == "unavailable"
    assert summary["official_period_complaints"] is None
    assert summary["prior_official_counts_file_present_but_not_refreshed"] is True
    assert "9999" in old.read_text()  # unchanged historical file; NOT this run's result


def test_strict_counts_still_fail(tmp_path, monkeypatch):
    setup_processed(tmp_path, monkeypatch)
    monkeypatch.setattr(pipeline, "download_monthly_counts", lambda *a: (_ for _ in ()).throw(
        trends.CFPBTrendsUnavailable("Trends unavailable")))
    with pytest.raises(trends.CFPBTrendsUnavailable):
        pipeline.run(False, 5000, "2024-01-01", "2024-12-31", reuse_processed=True,
                     require_official_counts=True)


def test_reuse_validates_requested_dates(tmp_path, monkeypatch):
    setup_processed(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="outside the specified window"):
        pipeline.run(False, 5000, "2026-01-01", "2026-12-31", reuse_processed=True,
                     skip_official_counts=True)


def test_skip_and_require_incompatible(tmp_path, monkeypatch):
    setup_processed(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Cannot both skip and require"):
        pipeline.run(False, 5000, "2024-01-01", "2024-12-31", reuse_processed=True,
                     skip_official_counts=True, require_official_counts=True)
