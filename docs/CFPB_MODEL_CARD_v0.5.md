# Model card — CFPB recorded-response relief classifier

**Status:** retrospective research demonstration, not production deployment.

**Model family:** scikit-learn logistic regression with balanced class weights, one-hot categorical preprocessing (`handle_unknown='ignore'`, `min_frequency=5`).

## Intended use

Teach and demonstrate reproducible probabilistic classification and review prioritization analysis on sampled public complaint data. It may inform *exploratory* analysis but is not cleared for automatic consumer decisions, company grading, investment use, or legal/regulatory findings.

## Target and predictor scope

Target `has_relief` indicates that the **company response category contains the word “relief.”** The target is a proxy for a reported response category. It does not confirm payment, consumer satisfaction, correctness, misconduct, or causation. Features are `company`, `product`, `sub_product`, `issue`, `state`, `submitted_via`. Narrative flag was excluded as nonvarying in the training data. Outcome/post-outcome fields are not predictors.

## Evaluation

Separate original 75/25 run and research 60/15/25 chronological experiment. Research test population: 1,222 (Oct 14–Dec 31, 2025). Raw ROC-AUC 0.7292, AP 0.4759, Brier 0.2167. Validation Platt calibration improves Brier to 0.1833 on those same test records; log loss is 0.5186. Calibrated ROC-AUC/AP do not improve. One validation-only raw-score threshold of 0.65 yields 81.7% test recall; calibration at 0.50 yields 31.9%. These are different operating points.

## Data and evaluation limitations

Systematic 5,000-row weekly-stratified sample; no evidence of population representativeness. Date-based split separates observation dates but the retrieved data have retrospective labels, so prospective point-in-time integrity is not fully established. Recorded relief prevalence shifts across periods. Employer/company identifiers can encode strongly heterogeneous recording outcomes. Experian test subgroup has 0 observed positive labels; this demands caution before interpreting group-level performance. Calibration assessed on one later test window, without confidence intervals or independent replication.

## Risks and human oversight

Potential selection bias; reporting-delay bias; category/label-mapping artifact; changes in public data availability; distribution shift; unfair or misleading company comparisons. Do not infer wrongdoing, allocate legal entitlements, or automate adverse consumer action from predictions. Any applied use needs explicit business costs, external testing, prospective follow-up, and stakeholder review.

## Reproduce and provenance

Scripts: `src/model.py`, `src/model_quality_research.py`, `scripts/evaluate_real_cfpb.py`, `cfpb_quality/`. Summary evidence: `docs/evidence/2026-10-22/`. Full predictions and source Parquet are excluded from the repository. See [research findings](CFPB_RESEARCH_FINDINGS_v0.5.md) for exact date ranges and comparisons.
