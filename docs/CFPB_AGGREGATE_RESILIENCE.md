# CFPB Aggregate Endpoint Resilience — v0.3

## The issue

The *optional* legacy monthly-trends API returned something `requests.Response.json()` could not decode in the user's October 2026 live run. The 5,000 cleaned complaint records were saved and the independent research evaluation ran successfully, but the older full pipeline stopped before writing a new `run_summary.json`.

CFPB's **September 2026 Release 24** says narrative and complaint visualizations were removed. That does not, by itself, prove the precise response received locally or when the trends API began failing. Do not make claims about the endpoint's status without validating the actual HTTP response and the supported API contract. See https://cfpb.github.io/api/ccdb/release-notes.html

## Changes

- `src/trends.py`: raises an informative `CFPBTrendsUnavailable` if a successful HTTP response contains non-JSON or unexpected JSON. Retains regular parsing of the historical trends response when available.
- `src/pipeline.py`: treats aggregate fetch as optional by default; a failure is recorded in `run_summary.json` as **`official_counts_status: unavailable`**, without inventing population counts.
- `--require-official-counts`: requests historical all-or-nothing behavior for workflows that depend on a fresh population aggregate.
- `--skip-official-counts`: bypasses the old endpoint entirely; `official_counts_status: skipped`.
- `--reuse-processed`: uses the already validated `data/processed/complaints.parquet` and does not overwrite it or make another live detail download. It verifies the processed records lie within the specified date range. The original sample-selection method is not re-verified from a processed file alone.

**Any existing `artifacts/official_monthly_counts.csv` is left untouched if the fetch fails or is skipped. It must NOT be presented as newly refreshed.** `run_summary.json` flags this explicitly. Power BI historical screenshots must be labeled by the run that produced their aggregates, rather than treated as current evidence.

## Complete the pipeline without a second 5,000-record download

In the repository's activated venv:

```powershell
python -m pytest -q
python -m src.pipeline --reuse-processed --skip-official-counts --start-date 2025-01-01 --end-date 2025-12-31
python -c "import json; x=json.load(open('artifacts/run_summary.json', encoding='utf-8')); print('Detail rows:', x['detail_sample_rows']); print('Official counts status:', x['official_counts_status']); print('Total from refreshed official population:', x['official_period_complaints'])"
```

Expected `official_counts_status` is `skipped`; `official_period_complaints` is `None`, not 5,000 and not the historical annual total.

## Using the optional trends feed

To attempt a fresh monthly aggregate but still complete the detail pipeline on an error:

```powershell
python -m src.pipeline --reuse-processed --start-date 2025-01-01 --end-date 2025-12-31
```

If a downstream report requires a fresh official monthly aggregate, make failure fatal:

```powershell
python -m src.pipeline --reuse-processed --require-official-counts --start-date 2025-01-01 --end-date 2025-12-31
```

Never substitute the 5,000-record detail sample for the 2025 full-population aggregate. The earlier reported population count (5,442,964) is prior-run evidence, not newly confirmed here. Alternative aggregate sources must be revalidated and sourced before changing the README or dashboard claims.

## Research evaluation remains separate

`python -m scripts.evaluate_real_cfpb --data data/processed/complaints.parquet --out artifacts/model_quality_real --data-kind cfpb_sample`

This evaluates a three-way chronological *detail sample* model and does not depend on full-population monthly counts. It does not update the repository's original 75/25 experiment.

## Remaining limitations

- CFPB releases in 2026 changed visible fields and output formats; especially reassess the `has_narrative` feature for newly acquired data.
- A Brier score on one chronological split is not a deployment-readiness guarantee.
- Keep exact data provenance and the date each aggregate was obtained.
