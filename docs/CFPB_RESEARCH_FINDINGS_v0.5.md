# Research findings — CFPB complaint-response prediction

**Evidence review date:** October 22, 2026

**Research code version:** v0.4 feature-audit integration (local Windows run)

**Evidence:** `docs/evidence/2026-10-22/model_quality.json`, `research_experiment.json`, raw and calibrated reliability charts. The JSONs are exact copies of uploaded local metrics; the calibrated chart is drawn from its reported reliability-bin summary.

## Executive finding

A logistic regression trained on 3,026 earlier records and calibrated on 752 intermediate records achieved a test Brier score of **0.183321** on 1,222 later CFPB complaint records. The same uncalibrated model scored **0.216748**; a training-prevalence constant model scored **0.237103**. Relative reduction versus uncalibrated: **15.42%** (Brier, not an improvement in ROC-AUC or demonstrated business value).

## Research question

Can intake-related categorical complaint fields estimate the *recorded company-response relief category* on future sampled complaints, and does separately fitted sigmoid calibration improve probability scoring?

## Data and leakage controls

- **Input:** existing 2025 CFPB processed Parquet, 5,000 complaints reused from a local run; selection procedure was not reverified in the final reuse run.
- **Target:** `has_relief` is derived from whether the recorded `company_response` field contains `relief`; this is a response-category proxy, not a financial payout measure.
- **Features:** company, product, sub-product, issue, state, submitted-via. `has_narrative` excluded due to train-constant status and zero values for all 5,000 observations.
- **Train:** 3,026 complaints, 2025-01-07 through 2025-08-12.
- **Validation:** 752 complaints, 2025-08-19 through 2025-10-07.
- **Test:** 1,222 complaints, 2025-10-14 through 2025-12-31.
- Same-date complaints are kept in the same split. No test-label use in classifier fitting, calibration fitting, or validation threshold selection is apparent from the reviewed source snapshot.
- The dataset was retrieved after the complaint dates. No point-in-time source snapshot was provided; late response labels and revised records may limit prospective reproducibility.

## Probability scoring: final holdout

| Measure | Constant (train prevalence 0.4511) | Raw logistic model | Validation-calibrated logistic model |
|---|---:|---:|---:|
| ROC-AUC | 0.5000 | 0.7292 | 0.7292 |
| Average precision | 0.3437 | 0.4759 | 0.4759 |
| Brier | 0.237103 | 0.216748 | **0.183321** |
| Log loss | 0.667278 | 0.605288 | **0.518609** |
| ECE, 10 equal-width bins | 0.10739 | 0.14840 | **0.08228** |

The calibration layer is a logistic regression of outcomes on validation-period logit scores. It leaves model ranking unchanged on this holdout. Ten-bin ECE is a noisy, bin-dependent diagnostic rather than an absolute guarantee that individual probabilities are calibrated.

## Thresholds and operating risk

| Statistic | Raw score cutoff 0.65 | Calibrated score cutoff 0.50 |
|---|---:|---:|
| Recall | 81.67% | 31.90% |
| Precision | 50.81% | 44.22% |
| Review/flag rate | 55.24% | 24.80% |
| TN / FP / FN / TP | 470 / 332 / 77 / 343 | 633 / 169 / 286 / 134 |

The raw cutoff of `0.65` was chosen using the **validation period** for a minimum target recall of 80%; that period's measured recall was **85.83%**. The calibrated cutoff `0.50` was not chosen to satisfy the same operating constraint. **Do not claim the calibrated classifier is a better operational triage policy from these comparisons.** Before application, choose a calibration-aware decision threshold from separate validation data and evaluate costs, review capacity, and distribution shift.

## Distributions and subgroup diagnostic cautions

- Test recorded-relief prevalence: **34.37%**, compared with training prevalence **45.11%** (10.74 percentage-point decrease). Date and label distribution shift materially affect probability estimates.
- Credit reporting/personal consumer reports: **1,081 / 1,222** test complaints (88.46%), with subgroup raw-model ROC-AUC approximately **0.7058**.
- Debt collection: **69** test records, raw-model ROC-AUC approximately **0.5240**; smaller groups are especially unstable.
- Equifax: **363** records, ROC-AUC **0.5175**; TransUnion: **366** records, ROC-AUC **0.4783**. Experian: **280** records, **zero recorded positive labels**, so ROC-AUC is undefined. Those are descriptive **sample results**, not proof of quality or wrongdoing by a company.
- The marked company-level label differences merit a label-encoding and company-stratified validation audit. Company identity may encode recording practices, complaint mix, and policies rather than a portable risk relationship.

## Original separate 75/25 experiment (NOT directly comparable)

The existing model with 3,750 training and 1,250 testing records produced ROC-AUC **0.7327**, average precision **0.4807**, accuracy **0.6760**, precision **0.5138**, and recall **0.9202**. This model had a different temporal training window and cutoff. Present it independently; do not call the difference between the 75/25 and 60/15/25 experiments a performance gain or loss.

## Reporting scope and limitations

1. The historical **5,442,964** 2025 complaint aggregate from an earlier project snapshot was **not regenerated** in the final run; `official_counts_status` was `skipped`. Older dashboard counts should be labeled archival and not current.
2. The 5,000-record sample is systematic/weekly-stratified, not a population-representative probability sample.
3. The outcomes are publicly recorded administrative response labels and can lag or change after initial receipt.
4. Neither ROC-AUC nor calibration proves suitability for consumer intervention, fairness, or financial returns.
5. No uncertainty intervals, external dataset replication, prospective study, or company-composition-adjusted inference is supplied in this evidence snapshot.
6. Complaint-level CSV outputs remain private/local under `artifacts/`; the committed summary evidence has no complaint IDs or row-level predictions.

## Reproduction and audit trail

To recreate the user-observed model outputs with the **same processed dataset**:

```powershell
python -m pytest -q
python -m src.pipeline --reuse-processed --skip-official-counts --start-date 2025-01-01 --end-date 2025-12-31
python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet --out artifacts/model_quality_real --data-kind cfpb_sample
```

The archived `input_sha256` in model-quality JSON fingerprints the full local row-level prediction CSV, which is intentionally not committed. Independent third parties cannot recreate these exact scores without the same source snapshot. Unit tests and the published-evidence consistency tests validate software logic and snapshot integrity; they are not independent external replication.

## Decision

**Publish as an analytically defensible research case study with limitations.** Do not market it as production risk scoring or claim that Platt calibration improves recall at a common threshold. Prioritize a further label-audit and calibration-aware threshold comparison before any applied triage recommendation.
