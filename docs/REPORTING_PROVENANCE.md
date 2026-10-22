# Dashboard data provenance

The Power BI gallery contains screenshots from an earlier consumer-complaint reporting build. Two distinct inputs must not be conflated.

| Analytical layer | What is supported | Boundary |
|---|---|---|
| Complaint-level detail | 5,000 retrieved and processed 2025 complaint records, re-evaluated in the October 22, 2026 research run | Systematic weekly sampling; not a representative population sample |
| Historical monthly trends | Previously captured aggregate dashboard trends | The optional aggregate source was **not refreshed** during the October 2026 run; the original retrieval timestamp is not retained in the published evidence |
| Original classifier | 1,250-row chronological holdout, ROC-AUC 0.7327 | Different split/model evaluation from the research calibration result |
| Research calibration | 1,222-row later chronological holdout, Brier 0.2167 before and 0.1833 after calibration | Scores reflect a recorded-response-category proxy; not confirmed financial relief |

For repeatable verification, use the [model card](CFPB_MODEL_CARD_v0.5.md), [research findings](CFPB_RESEARCH_FINDINGS_v0.5.md), and the published [research aggregate evidence](evidence/2026-10-22/). The public [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) is the underlying complaint source.

These screenshots should not be interpreted as newly verified October 2026 population totals or production measurements. This reporting distinction is intentional; **no historical aggregate figure has been invented or refreshed in this documentation update**.
