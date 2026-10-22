"""Run with python -m cfpb_quality --predictions CSV --out DIR."""
import argparse
from .report import create_report


def main():
    parser = argparse.ArgumentParser(description="Offline CFPB model-quality diagnostics")
    parser.add_argument("--predictions", required=True, help="Train/validation/test predictions CSV")
    parser.add_argument("--out", default="artifacts/model_quality")
    parser.add_argument("--min-group-n", type=int, default=50)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--no-calibration", action="store_true")
    parser.add_argument("--data-kind", choices=("synthetic", "cfpb_sample", "unverified"), default="unverified")
    args = parser.parse_args()
    result = create_report(args.predictions, args.out, min_group_n=args.min_group_n,
                           minimum_recall=args.min_recall, calibrate=not args.no_calibration,
                           data_kind=args.data_kind)
    print(f"Created {args.out}/model_quality.json and test_reliability.png")
    print(f"Test Brier score: {result['test_model']['brier_score']:.4f}")
    print(f"Constant baseline Brier: {result['test_constant_baseline']['brier_score']:.4f}")


if __name__ == "__main__":
    main()
