# Historical CFPB narrative NLP — optional research module

This project adds a **separate, local-only** historical-narrative experiment to the existing structured CFPB analytics and relief model. No change to `src/pipeline.py`, the existing Power BI dashboard, or the original evaluated model is required.

## Source availability and provenance

On **August 14, 2026**, the CFPB ceased publishing narratives in its live Complaint Database. The structured 2025 detail sample used for the existing project contained **zero nonempty narrative texts** in the October 2026 audit. Neither that sample nor the current API should be described as a narrative dataset.

The CFPB maintains a [historical narratives archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/) with official ZIP exports covering several historical periods, including 2025. Download a desired ZIP to `data/raw/` without unpacking it. Do **not** commit complaint narratives, large data files, embedding caches, or query results. These public narratives represent consented, edited, unverified allegations, not verified facts or a representative sample of consumers.

## Setup and demonstration

From the repository root using Python 3.12:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-nlp.txt
python -m pytest -q tests/test_nlp.py
python -m scripts.make_nlp_fixture
python -m scripts.run_nlp --data data/sample/nlp_synthetic.csv --source-kind synthetic --query "My loan was paid off but still shows a balance" --benchmark --out artifacts/nlp/synthetic_metrics.json
```

**The generated fixture is entirely synthetic.** Its classification metrics are an engineering smoke test, **not** evidence of CFPB classification performance. The first embedding run may download the free pretrained MiniLM model; subsequent runs can use its cache. There are no paid APIs or hosted services.

Historical data run after downloading an archive ZIP:

```powershell
python -m scripts.run_nlp --data data/raw/YOUR_ARCHIVE_FILENAME.zip --source-kind cfpb_archive --max-rows 5000 --benchmark --query "I paid my loan but the balance still appears outstanding" --out artifacts/nlp/historical_metrics.json
```

The ZIP is streamed in chunks; seeded reservoir sampling selects up to 5,000 nonempty historical narratives across the entire selected archive, rather than a first-page extract. Complaint IDs and exact text duplicates are removed after sampling. Dates and source-file SHA-256 are recorded in the aggregate JSON report. The model does **not** assume that the unrelated existing 5,000-record structured sample contains narratives.

## Methods

- **Retrieval:** `sentence-transformers/all-MiniLM-L6-v2` generates normalized sentence embeddings. Exact cosine similarity ranks the locally loaded narratives; top-k complaint IDs and excerpts print to the terminal only. No vector database, chatbot, or remote embedding API is used.
- **Text classification:** predict CFPB `Product` labels (a categorization, **not** complaint merit or financial risk). Compare a most-frequent training-class baseline, word/bigram TF-IDF + balanced logistic regression, and MiniLM embeddings + balanced logistic regression. Only training-period counts determine the retained categories; the benchmark is not a complete CFPB taxonomy classifier.
- **Evaluation:** split by **received date** (earlier 75% of unique dates for training, later dates for test). Remove test narratives almost identical to a training narrative using train-fitted character n-gram TF-IDF cosine similarity ≥0.98. Report class distributions, accuracy, macro-F1, per-class precision/recall/F1/support, and confusion matrices.
- **Privacy:** the aggregate JSON report contains no complaint narrative text or prediction-level records. Query excerpts appear only in the local terminal; review source content before screenshots or publication.

## Limitations

The published narratives are a selectively available historical subset. The archive ZIP's period determines the study interval; there is no ongoing narrative feed. Exact cosine retrieval with 5,000 candidates is deliberately simple. The lexical near-duplicate check is heuristic and cannot eliminate every paraphrase. Class imbalance, category drift, short time windows, and the selection of only represented training categories limit generalization. A single chronological holdout is not evidence of production accuracy. Do not assert MiniLM outperforms TF-IDF without reporting an actual comparative run on historical narratives.
