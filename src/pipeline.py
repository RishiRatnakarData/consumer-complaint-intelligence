"""Command-line entry point for the complete project."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]

from src.database import build_database  # noqa: E402
from src.ingest import download_cfpb, load_sample  # noqa: E402
from src.model import fit_relief_model  # noqa: E402
from src.transform import clean_complaints, quality_report  # noqa: E402
from src.trends import CFPBTrendsUnavailable, download_monthly_counts  # noqa: E402
from src.sampling import download_weekly_stratified_sample  # noqa: E402


def run(
    sample: bool,
    limit: int,
    start_date: str,
    end_date: str | None = None,
    *,
    reuse_processed: bool = False,
    skip_official_counts: bool = False,
    require_official_counts: bool = False,
) -> None:
    if skip_official_counts and require_official_counts:
        raise ValueError("Cannot both skip and require official counts")
    if sample and reuse_processed:
        raise ValueError("Cannot use --sample and --reuse-processed together")
    if reuse_processed:
        source = ROOT / "data" / "processed" / "complaints.parquet"
        if not source.exists():
            raise FileNotFoundError(f"No processed complaints at {source}; run a live download first")
        clean = pd.read_parquet(source)
        if "date_received" not in clean.columns:
            raise ValueError("Processed dataset lacks date_received")
        actual = pd.to_datetime(clean["date_received"], errors="coerce", utc=True)
        if actual.isna().any() or clean.empty:
            raise ValueError("Processed dataset contains invalid dates or no rows")
        # Compare UTC calendar dates directly to avoid timedelta unit ambiguity.
        if actual.min().date() < pd.Timestamp(start_date).date() or (
            end_date is not None and actual.max().date() > pd.Timestamp(end_date).date()
        ):
            raise ValueError("Existing dataset dates are outside the specified window; check --start-date and --end-date")
        sample_method = "reused_existing_processed_detail_dataset; original selection not reverified"
    elif sample:
        raw = load_sample(ROOT)
        sample_method = "committed_fixture"
    elif end_date is not None:
        raw = download_weekly_stratified_sample(
            limit,
            start_date,
            end_date,
        )
        sample_method = "weekly_stratified_detail_sample"
    else:
        raw = download_cfpb(
            limit,
            start_date,
        )
        sample_method = "latest_records_detail_sample"
    if not reuse_processed:
        clean = clean_complaints(raw)
    report = quality_report(clean)

    if not report["passed"].all():
        raise ValueError(f"Data quality failed:\n{report}")

    processed = ROOT / "data" / "processed"
    artifacts = ROOT / "artifacts"
    processed.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

    if not reuse_processed:
        clean.to_parquet(
            processed / "complaints.parquet",
            index=False,
        )
    report.to_csv(
        artifacts / "quality_report.csv",
        index=False,
    )

    outputs = build_database(
        clean,
        processed / "complaints.duckdb",
        ROOT / "sql" / "models.sql",
    )
    for name, frame in outputs.items():
        frame.to_csv(
            artifacts / f"{name}.csv",
            index=False,
        )

    metrics = fit_relief_model(
        clean,
        artifacts / "model_metrics.json",
    )

    official_counts = None
    official_counts_path = (
        artifacts / "official_monthly_counts.csv"
    )

    official_counts_status = "not_requested"
    official_counts_error = None
    if not sample and end_date is not None:
        if skip_official_counts:
            official_counts_status = "skipped"
            print("NOTICE: Skipping optional official monthly counts; any existing CSV is NOT refreshed.")
        else:
            try:
                official_counts = download_monthly_counts(start_date, end_date)
                official_counts.to_csv(official_counts_path, index=False)
                official_counts_status = "fresh"
            except (CFPBTrendsUnavailable, requests.RequestException, ValueError, RuntimeError) as exc:
                official_counts_status = "unavailable"
                official_counts_error = f"{type(exc).__name__}: {exc}"
                if require_official_counts:
                    raise
                print(f"WARNING: Official monthly counts unavailable: {official_counts_error}")
                print("WARNING: Retaining any prior official_monthly_counts.csv unchanged; it is NOT this run's evidence.")
    elif sample and official_counts_path.exists():
        official_counts_path.unlink()

    summary = {
        "detail_sample_method": sample_method,
        "mode": "sample" if sample else "live",
        "detail_sample_rows": len(clean),
        "detail_sample_min_date": str(
            clean["date_received"].min().date()
        ),
        "detail_sample_max_date": str(
            clean["date_received"].max().date()
        ),
        "requested_start_date": (
            None if sample else start_date
        ),
        "requested_end_date": (
            None if sample else end_date
        ),
        "quality_checks_passed": int(
            report["passed"].sum()
        ),
        "processed_data_reused": reuse_processed,
        "official_counts_status": official_counts_status,
        "official_counts_error": official_counts_error,
        "prior_official_counts_file_present_but_not_refreshed": (
            official_counts_status in {"unavailable", "skipped"} and official_counts_path.exists()
        ),
        "official_months": (
            len(official_counts)
            if official_counts is not None
            else None
        ),
        "official_period_complaints": (
            int(
                official_counts[
                    "official_complaint_count"
                ].sum()
            )
            if official_counts is not None
            else None
        ),
        "model": metrics,
    }

    (artifacts / "run_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use the committed 12-row sample",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
    )
    parser.add_argument(
        "--start-date",
        default="2024-01-01",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional maximum complaint-received date",
    )
    parser.add_argument(
        "--reuse-processed",
        action="store_true",
        help="Reuse the existing processed Parquet; do not redownload detail complaints",
    )
    parser.add_argument(
        "--skip-official-counts",
        action="store_true",
        help="Skip the optional legacy monthly-trends endpoint; do not refresh its CSV",
    )
    parser.add_argument(
        "--require-official-counts",
        action="store_true",
        help="Fail the full run if the optional official monthly counts are unavailable",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
    )
    args = parser.parse_args()

    if args.clean_output:
        for folder in [
            ROOT / "data" / "processed",
            ROOT / "artifacts",
        ]:
            if folder.exists():
                for child in folder.iterdir():
                    if child.name != ".gitkeep":
                        if child.is_dir():
                            shutil.rmtree(child)
                        else:
                            child.unlink()
        return

    run(
        args.sample,
        args.limit,
        args.start_date,
        args.end_date,
        reuse_processed=args.reuse_processed,
        skip_official_counts=args.skip_official_counts,
        require_official_counts=args.require_official_counts,
    )


if __name__ == "__main__":
    main()