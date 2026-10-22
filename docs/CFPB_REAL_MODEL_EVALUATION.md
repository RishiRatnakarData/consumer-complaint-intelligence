# CFPB: real-data model-quality integration (research experiment v0.2)

## Why an additional experiment?

The existing `src.model.fit_relief_model` is **unchanged**, uses a chronological
75/25 train/test split, and writes `artifacts/model_metrics.json`. Its originally
reported metrics describe that specific training design.

The new `src.model_quality_research` uses the **same seven predictor fields,
encoder and logistic-regression specification**, but fits on approximately 60%
of received records, uses the next approximately 15% for probability calibration
and operating-threshold selection, and evaluates on the most recent 25%. Date
boundaries do not cross splits. It therefore does **not** represent an identical
model instance or an apples-to-apples improvement over the original model.

Only the training period is used to fit the classifier. Validation targets may
inform sigmoid calibration and threshold selection. Test labels are used only
for final evaluation. The package checks unique IDs, strict date ordering,
training/validation/test class coverage, and minimum sample sizes.

## Run in Windows PowerShell from original repository directory

The add-on v0.1 must already be installed and the existing `.venv` activated.

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-quality.txt
python -m pytest -q
python -m src.pipeline --sample
```

**To use your existing 2025 live run if it is saved locally:**

```powershell
Test-Path .\data\processed\complaints.parquet
python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet --out artifacts/model_quality_real --data-kind cfpb_sample
```

If `Test-Path` prints `False`, the last committed offline fixture or an absent
live-data run cannot substitute for the real 5,000-record details. Regenerate
only if you want a fresh API snapshot (live data may have changed):

```powershell
python -m src.pipeline --limit 5000 --start-date 2025-01-01 --end-date 2025-12-31
python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet --out artifacts/model_quality_real --data-kind cfpb_sample
```

Inspect output locally:

```powershell
explorer .\artifacts\model_quality_real
Get-Content .\artifacts\model_quality_real\model_quality.json
```

## What the files mean

- `real_holdout_predictions.csv`: one row per cleaned sampled complaint, labels,
  predicted probabilities and split labels (kept local under ignored `artifacts/`).
  Its **training** predictions are in-sample and not valid independent performance
  estimates. Only validation/test scores are out-of-sample.
- `research_experiment.json`: model specifications, sample sizes, caveats.
- `model_quality.json`: Brier/log loss, calibration, ROC-AUC and average
  precision, training-prevalence constant baseline, validation-only threshold,
  subgroup descriptive metrics (minimum sample count), data-scope notes.
- `test_reliability.png`: uncalibrated model's test-period reliability chart.

### Interpreting scores responsibly

Lower Brier or log loss is better. A lower score than the constant baseline
indicates superior probability prediction **for this held-out sample**; it does
not prove production deployment suitability or universal superiority. The
post-hoc Platt calibration is fitted on validation and may help or worsen Brier.
The raw-score threshold targets a validation recall minimum of 0.80 when
feasible; the achieved recall on test may be lower. Check actual test results.
The 10-bin ECE and subgroup metrics are unstable when samples are small.

### Limits and non-leakage concerns

- The population total of 5,442,964 in the earlier study is an aggregate
  and **not** the number of supervised model training rows. Research uses only
  the processed complaint-level detail sample (usually 5,000 rows).
- The weekly selection is systematic and not a probability sample; group
  statistics are not prevalence or company-quality estimates for the U.S.
- Company responses are post-intake outcomes; recent complaints can be
  censored or incomplete at the query date, even with a chronological split.
- The `has_narrative` flag must be verified as available at the intended
  scoring time; CFPB public narrative release may lag receipt.
- Old records may be revised by the API, and no point-in-time feature or
  label snapshots are available here. Neither date splitting nor testing can
  eliminate this limitation.
- Prediction outputs are locally generated analytics, not an automatic
  disposition or intervention tool. Keep `artifacts/` excluded from Git.
- Genuine CFPB results must come from the user-run historical/updated detail
  data; test fixture results are synthetic and not resume evidence.

## Review criteria before publishing

1. All prior model tests and new research tests pass on Windows.
2. Save your actual test Brier vs train-prevalence benchmark and dates.
3. Verify the user-run input is the intended 2025 5,000-record sample.
4. Compare calibrated vs uncalibrated **within this research experiment**.
5. If revising headline resume metrics, only use accurately documented
   supported results; don't replace original 75/25 metrics implicitly.
6. Do not commit local row-level prediction files or proprietary/sensitive data.

**Provenance flag:** the CLI defaults to `unverified`. Use `--data-kind cfpb_sample` only after confirming the processed Parquet was generated by your actual CFPB live-data pipeline. This tag represents your input verification, not an independent third-party audit.
