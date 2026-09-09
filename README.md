# Consumer Finance Complaint Intelligence

[![CI](https://github.com/RishiRatnakarData/consumer-complaint-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/RishiRatnakarData/consumer-complaint-intelligence/actions/workflows/ci.yml)

An end-to-end analytics project that uses public Consumer Financial Protection Bureau data to examine complaint volume, response patterns, relief outcomes, and product issues. The project combines a full-population monthly series with a reproducible detail sample, tested Python pipelines, DuckDB analytical models, an interpretable classifier, and Power BI-ready outputs.

> **Status:** Complete — live pipeline and Power BI dashboard validated.

## Business questions

1. How did total complaint volume change throughout 2025?
2. Which product and issue combinations dominate the detail sample?
3. How do response and relief classifications vary among companies?
4. Can information available near complaint intake help identify complaints likely to receive relief?

## Data design

The project deliberately separates two analytical datasets:

- **Official monthly population totals:** All 5,442,964 CFPB complaints recorded across the 12 months of 2025.
- **Weekly-stratified detail sample:** 5,000 complaint records distributed across weekly windows from January through December 2025.

The official aggregate series supports volume trends. The detail sample supports exploratory breakdowns, quality checks, SQL analysis, and modeling. Sample counts are never presented as full-population company or product totals.

Within each weekly window, the API returns the latest available records. Therefore, the detail dataset is a systematic time-stratified sample rather than a simple random sample.

## Key results

- CFPB recorded **5,442,964 complaints during 2025**.
- Monthly volume increased from the February low of **335,236** to the October peak of **519,786**, a **55.1% increase**.
- All **5 documented data-quality checks** passed for the 5,000-row detail sample.
- Credit reporting represented **4,379 of 5,000 sampled complaints (87.6%)**.
- “Incorrect information on your report” represented **58.2%** of sampled credit-reporting complaints.
- The sampled relief rate was **40.6%**, while **99.6%** of sampled complaints had a timely response.
- Relief classification varied sharply among the three largest sampled companies:
  - TransUnion: **63.3%**
  - Equifax: **63.2%**
  - Experian: **0.7%**
- That company difference is descriptive, not a quality ranking. It largely reflects non-monetary-relief classifications for TransUnion and Equifax versus explanation classifications for Experian.

## Modeling results

A logistic-regression model predicts whether a complaint receives monetary or non-monetary relief.

Features are limited to information available near complaint intake:

- Company
- Product and sub-product
- Issue
- State
- Submission channel
- Narrative availability

Company response, timely-response status, and relief fields are excluded from the predictors to prevent outcome leakage.

The model uses the earliest 75% of records for training and the latest 25% for testing.

| Metric | Result |
|---|---:|
| Training rows | 3,750 |
| Test rows | 1,250 |
| Baseline accuracy | 65.92% |
| Model accuracy | 67.68% |
| Balanced accuracy | 73.61% |
| ROC-AUC | 73.30% |
| Average precision | 48.19% |
| Precision | 51.44% |
| Recall | 92.25% |
| F1 score | 66.05% |

The model identifies most relief cases but produces many false positives. It is suitable as a prioritization demonstration, not as an automated decision system or causal model.

## Recommendation

Prioritize operational review of credit-reporting complaints involving incorrect report information, while separately auditing how major credit bureaus classify “explanation” and “non-monetary relief” responses. Company comparisons should not be converted into quality rankings until complaint counts are normalized by company size, market share, and customer exposure.

## Dashboard

### Executive Overview

![Power BI Executive Overview](docs/images/dashboard_overview.png)

### Company Benchmark

![Power BI Company Benchmark](docs/images/company_benchmark.png)

### Product & Issue Detail

![Power BI Product and Issue Detail](docs/images/product_issue_detail.png)

The report contains three pages:

1. **Executive Overview** — official monthly complaint volume and sampled response outcomes.
2. **Company Benchmark** — descriptive company-level complaint, relief, and narrative comparisons.
3. **Product & Issue Detail** — an interactive product filter and ranked issue analysis.

The dashboard build specification is documented in [`docs/power_bi.md`](docs/power_bi.md). Generated datasets can be recreated by running the pipeline.

## Quick start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
python -m ruff check .
python -m src.pipeline --sample
```

Run the validated 2025 live-data build:

```powershell
python -m src.pipeline --limit 5000 --start-date 2025-01-01 --end-date 2025-12-31
```

Generated analytical files are written to `artifacts/`. Processed Parquet data and the DuckDB database are written to `data/processed/`. These outputs are ignored by Git and can be reproduced from the commands above.

## Architecture

```text
CFPB complaint API
├── Official trends endpoint
│   └── Full-population monthly complaint totals
└── Search endpoint
    └── Weekly-stratified complaint detail sample
        └── Validation and transformation
            ├── Parquet detail table
            ├── DuckDB analytical views
            ├── CSV dashboard datasets
            └── Relief-outcome model
```

See [architecture and design decisions](docs/architecture.md) for implementation details.

## Repository map

```text
src/ingest.py          cursor-based API ingestion and retries
src/sampling.py        weekly time-stratified detail sampling
src/trends.py          official monthly population totals
src/transform.py       validation, normalization, and features
src/database.py        DuckDB loading and SQL execution
src/model.py           leakage-aware relief model
src/pipeline.py        command-line orchestration
sql/models.sql         KPI, company, and product-issue views
tests/                 ingestion, sampling, trends, model, and transform tests
docs/                  architecture and Power BI instructions
data/sample/           small offline fixture used by CI
.github/workflows/     automated lint, tests, and sample build
```

## Data quality

The pipeline verifies:

1. The cleaned table contains records.
2. Complaint IDs are unique.
3. Receipt dates are complete.
4. Product values are complete.
5. Timeliness values are binary when labeled.

The current API does not provide usable consumer-dispute labels for this dataset, so the project excludes dispute-rate reporting rather than treating unknown values as “No.”

## Testing and reproducibility

- **7 automated tests** cover transformations, duplicate handling, API cursor pagination, weekly sampling, monthly trends, and model behavior.
- Ruff checks Python code quality.
- GitHub Actions runs linting, tests, and the offline sample pipeline on pushes and pull requests.
- CI does not depend on live CFPB availability.
- Generated data, local databases, virtual environments, secrets, and Power BI files are excluded from Git.

## Limitations

- The 5,000 detail records are a systematic weekly-stratified sample, not the full complaint population or a random probability sample.
- Raw complaint counts do not account for company size, market share, customer exposure, or product mix.
- Complaint submissions reflect reporting behavior and are not independently verified accounts of company wrongdoing.
- Taxonomy and response-classification practices can change over time.
- Predictive associations do not establish causal effects.
- Model performance should be monitored for calibration and temporal drift before operational use.

## Next steps

- Add company exposure or market-share denominators.
- Add probability calibration and threshold analysis.
- Add taxonomy-drift monitoring.
- Consider PostgreSQL only after implementing and testing a genuine deployment path.

## Data source

[CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)

## Author

**Rishi Ratnakar**

[LinkedIn](https://www.linkedin.com/in/rishi-ratnakar) · [GitHub](https://github.com/RishiRatnakarData)
