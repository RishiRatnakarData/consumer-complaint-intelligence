"""CLI for optional offline semantic search and complaint-text benchmarking."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.nlp import (
    MODEL_NAME, classification_benchmark, load_narratives, semantic_search,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Local .csv or archive .zip")
    parser.add_argument("--source-kind", choices=["synthetic", "cfpb_archive"], required=True)
    parser.add_argument("--query", help="Local-only semantic search query")
    parser.add_argument("--benchmark", action="store_true", help="Evaluate three classifiers")
    parser.add_argument("--out", type=Path, default=Path("artifacts/nlp/benchmark.json"))
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--min-chars", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()
    if not args.query and not args.benchmark:
        parser.error("Specify --query and/or --benchmark")

    frame, audit = load_narratives(
        args.data, max_rows=args.max_rows, min_chars=args.min_chars, seed=args.seed
    )
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit(
            "Install optional NLP dependencies: python -m pip install -r requirements-nlp.txt"
        ) from exc
    encoder = SentenceTransformer(args.model)

    if args.query:
        results = semantic_search(frame, args.query, encoder, top_k=args.top_k)
        print("Search results (local terminal only; narratives are not saved):")
        for item in results:
            print(
                f"{item['complaint_id']} | {item['product']} | "
                f"cosine={item['similarity']:.5f}\n"
                f"  {item['narrative'][:240]}"
            )
    if args.benchmark:
        result = classification_benchmark(frame, encoder)
        report = {
            "source_kind": args.source_kind,
            "embedding_model": args.model,
            "data_audit": audit,
            "evaluation": result,
            "note": "Synthetic demonstration" if args.source_kind == "synthetic" else "Historical archival CFPB sample",
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Aggregate metrics (no narrative text) written to {args.out}")
        for name, metrics in result["model_results"].items():
            print(f"{name}: accuracy={metrics['accuracy']:.5f}; macro_F1={metrics['macro_f1']:.5f}")


if __name__ == "__main__":
    main()
