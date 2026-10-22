# CFPB research evaluation — locally reported results, October 2026

User-provided console output from an evaluation on 5,000 processed complaint rows:

| Split | Rows |
|---|---:|
| Train | 3,026 |
| Validation | 752 |
| Test | 1,222 |

| Test prediction approach | Brier score (lower is better) |
|---|---:|
| Constant training-prevalence baseline | 0.2371 |
| Uncalibrated logistic-regression probabilities | 0.2167 |
| Platt-calibrated logistic-regression probabilities | 0.1833 |

These are reported console outputs, not independently re-executed against the user’s raw or processed dataset in this patch. Verify the JSON and predicted-probability CSV before citing on the resume or GitHub. The validation period fits the Platt transformation; the test period measures holdout performance. The original 75/25 model's ROC-AUC from an earlier run must not be presented as the score of the newer three-way model.

**Report-writing requirements:**

1. Verify the split date ranges, class prevalence in train/validation/test, subgroup counts and class diversity.
2. Compare calibration and discrimination without claiming external validity or causal effects.
3. Label `has_relief` as a post-intake **company-response** outcome; not independent evidence of whether an individual complaint deserved relief.
4. State that the 5,000-record weekly-sampled detail dataset is distinct from the earlier full-population monthly counts; do not extrapolate totals from the sample.
5. Check whether the September 2026 CFPB removal of complaint narratives impacts the `has_narrative` feature; if all values are 0, remove or flag the feature in subsequent work.
6. Avoid implying the model made production decisions, saved money, or improved outcomes.

The v0.3 resilience patch does **not** change the trained model, prediction outputs, calibration method, or research metrics. It only improves robustness of the original general pipeline.
