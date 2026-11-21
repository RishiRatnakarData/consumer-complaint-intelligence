"""Generate a small, entirely fictional set of complaints for offline demonstrations."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

TEMPLATES = {
    "Mortgage": [
        "My mortgage servicer applied my monthly payment incorrectly and reported a late balance",
        "The escrow account for my home loan has the wrong insurance payment amount",
        "After refinancing my home loan the old mortgage account still shows an amount due",
        "My mortgage lender has not corrected the principal owed after an extra payment",
    ],
    "Credit card": [
        "I disputed a credit card charge, but the issuer has not reversed the transaction",
        "My card statement contains an unexpected interest fee despite paying the balance",
        "The bank froze my credit card account after I reported an unauthorized purchase",
        "My credit card rewards were incorrectly removed after an account adjustment",
    ],
    "Debt collection": [
        "A collection agency keeps calling about a debt that does not belong to me",
        "The debt collector continues to demand payment after receiving proof of settlement",
        "My account was sent to collections without a notice of the alleged original debt",
        "The collector has not corrected the reported debt amount after a payment dispute",
    ],
}


def create_fixture(path: Path, rows_per_class: int = 24) -> pd.DataFrame:
    if rows_per_class < 8:
        raise ValueError("Need at least eight rows per class")
    rows = []
    start_date = date(2024, 1, 1)
    for index in range(rows_per_class):
        for offset, (product, templates) in enumerate(TEMPLATES.items()):
            rows.append({
                "complaint_id": f"SYN-{index:03d}-{offset}",
                "date_received": (start_date + timedelta(days=index)).isoformat(),
                "product": product,
                "complaint_what_happened": (
                    f"{templates[index % len(templates)]}. "
                    f"Fictional reference {index + 100 + offset * 31}; "
                    f"the response was requested during billing cycle {index % 7 + 1}."
                ),
            })
    frame = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("data/sample/nlp_synthetic.csv"))
    args = parser.parse_args()
    frame = create_fixture(args.out)
    print(f"Created {len(frame)} fictional complaints at {args.out}")


if __name__ == "__main__":
    main()
