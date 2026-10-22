"""Evaluate the research model on locally processed CFPB complaint details.

Usage: python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.model_quality_research import run_real_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run 3-way chronological logistic-regression research on real complaint details"
    )
    parser.add_argument("--data", default="data/processed/complaints.parquet")
    parser.add_argument("--out", default="artifacts/model_quality_real")
    parser.add_argument("--min-group-n", type=int, default=50)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--data-kind", choices=("cfpb_sample", "unverified"),
                        default="unverified",
                        help="Specify cfpb_sample only after verifying the input came from the CFPB live pipeline")
    args = parser.parse_args()
    path = Path(args.data)
    if not path.is_file():
        parser.error(
            f"Processed input not found: {path}. Run the live CFPB pipeline first; "
            "the committed 12-row fixture is intentionally too small."
        )
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() == ".csv":
        frame = pd.read_csv(path)
    else:
        parser.error("Use a cleaned .parquet or .csv file")
    result = run_real_evaluation(
        frame, args.out, min_group_n=args.min_group_n,
        minimum_recall=args.min_recall, data_kind=args.data_kind,
    )
    quality = result["report"]
    print(f"Research experiment: {result['metadata']['counts']}")
    print(f"Uncalibrated test Brier: {quality['test_model']['brier_score']:.4f}")
    print(f"Training-prevalence baseline Brier: {quality['test_constant_baseline']['brier_score']:.4f}")
    if "test_platt_calibrated" in quality:
        print(f"Platt-calibrated test Brier: {quality['test_platt_calibrated']['brier_score']:.4f}")
    print(f"Real-data evaluation outputs: {Path(args.out).resolve()}")
    print("Only the 3-way research model was evaluated; original 75/25 results remain separate.")


if __name__ == "__main__":
    main()
