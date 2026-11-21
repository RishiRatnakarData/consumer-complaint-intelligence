# Historical CFPB narrative NLP - research findings

## Research scope

An exploratory benchmark using the official CFPB historical consumer-complaint narrative archive.

- Source file: `CCDB_Export_Jan_Feb_2025.zip`
- Source SHA-256: `11c18bb0973eed8f5e4f66e2979346af0671a3aefcb5a6b9eec73009d53cff64`
- Date range: 2025-01-01 to 2025-02-28
- Eligible narratives scanned: 265,357
- Sampled after deduplication: 3,623
- Model training rows: 2,885
- Temporal holdout rows: 518
- Holdout begins: 2025-02-14
- Product classes evaluated: 5
- Near-duplicate holdout rows excluded: 50

## Classification benchmark

| Model | Accuracy | Macro-F1 |
|---|---:|---:|
| Majority-class baseline | 0.7490 | 0.1713 |
| TF-IDF + logistic regression | 0.8263 | 0.6733 |
| MiniLM embeddings + logistic regression | 0.8147 | 0.6882 |

**Highest accuracy:** TF-IDF + logistic regression.

**Highest macro-F1:** MiniLM embeddings + logistic regression.

The task is historical CFPB product-category classification, not fraud detection, complaint-merit assessment, or consumer-risk prediction.

## Methods

- Seeded reservoir sampling across the selected historical archive.
- Deduplication and chronological train/test separation.
- Training-only selection of eligible product categories.
- Training-fitted near-duplicate screening.
- Majority-class, TF-IDF, and pretrained MiniLM embedding baselines.
- Accuracy, macro-F1, class-level metrics, and confusion matrices.

The complete aggregate metrics, including class-level results and source provenance, are available in [the evidence JSON](evidence/2026-11-20/historical_nlp_metrics.json).

## Interpretation and limitations

These results establish that the implemented classifiers can be evaluated on genuine historical CFPB narratives. They do not establish performance on future complaints or live operational data.

The source is a selectively published archive, not a representative sample of all CFPB complaints. Product-category imbalance and drift affect interpretation. The model comparison uses one chronological holdout and has no statistical significance analysis for between-model differences.

The differences between model scores are descriptive for this sample. No complaint-level narratives, excerpts, embeddings, or predictions are published with this report.

For reproducibility and details, see [the NLP methods document](CFPB_NLP.md).
