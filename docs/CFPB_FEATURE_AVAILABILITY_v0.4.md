# CFPB feature-availability review — v0.4

## Data observed in the October 22, 2026 local run

- The existing processed detail sample contained 5,000 complaint records received between 2025-01-07 and 2025-12-31.
- `has_narrative` equaled 0 in all 5,000 rows. This means **the downloaded dataset does not expose a non-empty narrative flag**. It does not establish that no consumers submitted narratives.
- Official population-wide monthly counts were skipped in the resilience run; the refreshed model uses only the 5,000 sampled rows.
- Original 75/25 logistic model reported ROC-AUC 0.7327, average precision 0.4807, and recall 0.9202 at its default probability threshold 0.5. These are **old-feature-set run** results, not v0.4 model results.
- Separate three-way research run used train=3026, validation=752, test=1222, reporting test Brier 0.2167 (uncalibrated), 0.2371 (training-prevalence baseline), and 0.1833 (validation-fitted Platt). These are also **pre-v0.4 results**. The separate research design has a different train/test split from the original model.

## Model design update

- Both the original model and the research model now test whether `has_narrative` has more than one distinct value **within the training period only**.
- A training-constant narrative flag is dropped from the active model input. The run's metrics or `research_experiment.json` include `features`, `excluded_features`, and `narrative_feature_audit` describing the selection.
- The raw `has_narrative` column is **not removed from the source data**; its values remain available for auditing.
- The original existing feature set remains unchanged when narrative status varies in training.
- The processed dataset is never modified by this patch.
- The pipeline's existing-date check compares UTC calendar dates without an ambiguous timedelta unit.

## How to rerun on the existing processed data

```powershell
python -m pytest -q
python -m src.pipeline --reuse-processed --skip-official-counts --start-date 2025-01-01 --end-date 2025-12-31
python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet --out artifacts/model_quality_real --data-kind cfpb_sample
Get-Content artifacts/model_metrics.json
Get-Content artifacts/model_quality_real/research_experiment.json
```

Caution: Rerunning the pipeline will overwrite **generated metrics, local DuckDB and some CSV outputs**, but the underlying Parquet is retained in `--reuse-processed` mode. Back up any manually edited outputs before rerun. Do **not** use sample mode for this check.

## Limitations and requirements before GitHub release

- User's 5,000-row sample is not the complete complaint population; population statistics must come from their own independently verified source and be dated appropriately.
- Confirm the latest run's full metrics, class imbalance, calibration, and subgroup results before updating resume numbers.
- Calibration is fitted on validation and evaluated on test, not a test-set refit. The Platt-calibrated classification threshold is 0.5 and is *not* the same as the validation-selected raw-score threshold.
- A single chronological evaluation is not enough to demonstrate long-run stability. Later work should add repeated forward-time backtests and feature/source-availability monitoring.
- Complaint narratives or empty proxies may have changed availability; treat population/source changes as possible data-contract drift and document them.
- No fabricated monthly totals, real-world outcomes, or claim of deployment into an actual loan/relief decision process.
