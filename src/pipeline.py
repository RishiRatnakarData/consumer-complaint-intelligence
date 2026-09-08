"""Command-line entry point for the complete project."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from src.database import build_database  # noqa: E402
from src.ingest import download_cfpb, load_sample  # noqa: E402
from src.model import fit_timeliness_model  # noqa: E402
from src.transform import clean_complaints, quality_report  # noqa: E402
from src.trends import download_monthly_counts  # noqa: E402


def run(
    sample: bool,
    limit: int,
    start_date: str,
    end_date: str | None = None,
) -> None:
    raw = (
        load_sample(ROOT)
        if sample
        else download_cfpb(limit, start_date, end_date)
    )
    clean = clean_complaints(raw)
    report = quality_report(clean)

    if not report["passed"].all():
        raise ValueError(f"Data quality failed:\n{report}")

    processed = ROOT / "data" / "processed"
    artifacts = ROOT / "artifacts"
    processed.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)

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

    metrics = fit_timeliness_model(
        clean,
        artifacts / "model_metrics.json",
    )

    official_counts = None
    official_counts_path = (
        artifacts / "official_monthly_counts.csv"
    )

    if not sample and end_date is not None:
        official_counts = download_monthly_counts(
            start_date,
            end_date,
        )
        official_counts.to_csv(
            official_counts_path,
            index=False,
        )
    elif official_counts_path.exists():
        official_counts_path.unlink()

    summary = {
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
    )


if __name__ == "__main__":
    main()