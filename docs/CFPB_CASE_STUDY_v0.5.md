# Case study — consumer complaint response analytics

**Problem:** A large consumer-finance complaint database has thousands of categorical attributes, changing publication interfaces, and delayed company-response fields. Analysts need transparent, reproducible reporting and appropriately qualified predictions—not misleading company league tables.

**Approach:** Implemented Python CFPB ingestion with deduplication and data-quality validation, Parquet/DuckDB/SQL reporting, and a Power BI dashboard. Used 5,000 processed 2025 CFPB complaint records in an independent chronological classification evaluation. Compared a class-weighted logistic regression with a training-prevalence baseline and validation-only Platt calibration.

**Verified October 22, 2026:** 53 local tests passed. Original classifier: ROC-AUC 0.7327 (1,250 test records). Research classifier: ROC-AUC 0.7292 (1,222 test records); Brier 0.2167 uncalibrated, 0.1833 calibrated, 0.2371 constant baseline. Calibration improved probabilistic scoring on this sample, without changing discrimination. The 5,000-record sample is not the earlier 5.44M population-level historical report.

**Challenge and decision:** The original optional trends endpoint returned a non-JSON response. A guarded recovery path allowed reporting and modeling to continue with the validated local Parquet while explicitly marking population counts as unavailable. The `has_narrative` field contained zero positives and was excluded using training-period information only. Threshold results revealed substantial precision/recall tradeoffs; no automatic triage policy was proposed.

**Limitations:** Nonprobability sample, delayed/revised labels, company-level target heterogeneity, training-test outcome shift, archived dashboards, and lack of prospective evaluation. No unverified impact, savings, deployment, or consumer-benefit claim.

**Technology:** Python, Requests, pandas, DuckDB, Parquet, SQL, scikit-learn, Matplotlib, Power BI, pytest, GitHub Actions.

**Evidence:** [Full research findings](CFPB_RESEARCH_FINDINGS_v0.5.md) · [Model card](CFPB_MODEL_CARD_v0.5.md) · [JSON and calibration plots](evidence/2026-10-22/)
