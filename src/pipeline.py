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


def run(sample: bool, limit: int, start_date: str) -> None:
    raw = load_sample(ROOT) if sample else download_cfpb(limit, start_date)
    clean = clean_complaints(raw)
    report = quality_report(clean)
    if not report["passed"].all():
        raise ValueError(f"Data quality failed:\n{report}")

    processed = ROOT / "data" / "processed"
    artifacts = ROOT / "artifacts"
    processed.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(processed / "complaints.parquet", index=False)
    report.to_csv(artifacts / "quality_report.csv", index=False)
    outputs = build_database(clean, processed / "complaints.duckdb", ROOT / "sql" / "models.sql")
    for name, frame in outputs.items():
        frame.to_csv(artifacts / f"{name}.csv", index=False)
    metrics = fit_timeliness_model(clean, artifacts / "model_metrics.json")
    summary = {
        "mode": "sample" if sample else "live",
        "rows": len(clean),
        "min_date": str(clean["date_received"].min().date()),
        "max_date": str(clean["date_received"].max().date()),
        "quality_checks_passed": int(report["passed"].sum()),
        "model": metrics,
    }
    (artifacts / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="Use the committed 12-row sample")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--clean-output", action="store_true")
    args = parser.parse_args()
    if args.clean_output:
        for folder in [ROOT / "data" / "processed", ROOT / "artifacts"]:
            if folder.exists():
                for child in folder.iterdir():
                    if child.name != ".gitkeep":
                        shutil.rmtree(child) if child.is_dir() else child.unlink()
        return
    run(args.sample, args.limit, args.start_date)


if __name__ == "__main__":
    main()

