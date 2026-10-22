"""Generate SYNTHETIC predictions solely for smoke testing; not CFPB results."""
from pathlib import Path
import numpy as np
import pandas as pd


def generate(path: str | Path, n: int = 1200, seed: int = 44):
    if n < 100:
        raise ValueError("n must be >=100")
    rng = np.random.default_rng(seed)
    z = rng.normal(size=n)
    company = rng.choice(["Alpha", "Beta", "Gamma"], size=n)
    product = rng.choice(["Credit", "Mortgage", "Banking"], size=n)
    p_true = 1 / (1 + np.exp(-(-0.45 + 0.8 * z + 0.15 * (product == "Credit"))))
    y = rng.binomial(1, p_true)
    predicted = np.clip(1 / (1 + np.exp(-(-0.20 + 0.65 * z))), 0.001, 0.999)
    train_end, val_end = round(0.6 * n), round(0.8 * n)
    split = ["train"] * train_end + ["validation"] * (val_end - train_end) + ["test"] * (n - val_end)
    df = pd.DataFrame({"complaint_id": np.arange(n),
                       "date_received": pd.date_range("2025-01-01", periods=n, freq="D"),
                       "split": split, "y_true": y, "y_prob": predicted,
                       "product": product, "company": company})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


if __name__ == "__main__":
    generate("demo_predictions.csv")
    print("Generated demo_predictions.csv with synthetic outcomes")
