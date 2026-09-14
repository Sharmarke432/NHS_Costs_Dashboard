NHS Cost Intelligence
An interactive, SQL-backed exploratory dashboard investigating variation in NHS service costs, built on the NHS National Cost Collection (NCC) 2024/25 dataset.

Live app: add your deployed URL here once live on Render

Project Question
What can NHS cost data tell us about variation in service costs?

This project is intentionally exploratory and descriptive. It identifies patterns, data-quality issues, and areas worth investigating further — it does not label any provider or service as efficient or inefficient. See Interpretation guardrails below for why, and how that's enforced throughout the app.

What This Project Demonstrates
Designing a DuckDB-backed analytical layer with parameterised SQL queries (no string interpolation) served through a multi-page Streamlit application

Applying robust statistics (median, activity-weighted median, IQR) instead of naive means on heavily skewed real-world cost data

Writing and maintaining a pytest suite covering database connections, query correctness, and data-exclusion logic, including catching and fixing a subset-comparison bug in test design itself

Building a self-building, reproducible deployment: the app constructs its DuckDB database from the committed source CSV on first run, so it works identically locally and on a fresh cloud deployment

Containerising the app with Docker and deploying it as an always-on web service on Render

Applying domain-appropriate caution when presenting healthcare cost data — avoiding causal or efficiency claims that the data cannot support

Dataset
Source: NHS National Cost Collection (NCC) 2024/25, National Cost Collection Index (NCCI) by Department and Service, MFF-unadjusted.

Approximately 38,562 numeric records with the following fields:

Field	Description
Provider	NHS provider identifier/name
Mapping_Pot	Descriptive grouping only — not a validated causal MFF variable
Service	Service code/description
Department	Department grouping
Activity	Activity volume
Unit_Cost	Reported unit cost
Actual_Cost	Actual total cost
Expected_Cost	Expected/benchmark total cost
Variance	Actual_Cost − Expected_Cost
NCCI	Index-like field; exact formula, denominator and scale not yet independently validated
Variance_Percent	Unstable when expected cost is small — treat with caution
Key Descriptive Findings
Reported unit cost is heavily right-skewed: median ≈ £405 vs. mean ≈ £1,874 — the mean is misleading for this data.

NCCI is centred near a median of 96, with a long tail extending to roughly 419 at the 99th percentile.

Median variance across all records is approximately −£3,295.

Providers with lower total activity show more scattered reported unit costs — consistent with a small-sample/denominator effect, not evidence of poor performance.

The highest activity-weighted unit-cost services include Paediatric Cardiac Surgery, Intermediate Care, Cardiac Surgery, Critical Care Transport, Paediatric Intensive Care, and Cardiothoracic Transplantation — a descriptive cost benchmark, not an efficiency ranking.

Mapping_Pot groups differ descriptively in typical cost and total activity; this does not establish a causal MFF effect.

Interpretation Guardrails
Because this dataset can easily be misused to imply provider performance judgements it cannot support, the project enforces a strict set of interpretive rules throughout the app, tests, and documentation:

Never claim a provider or service is "inefficient" based on cost or variance alone.

Never claim high cost means waste, or high variation proves poor performance.

Never treat Mapping_Pot as a causal driver of cost differences.

Never treat NCCI as a validated efficiency score without independently confirming its formula, denominator, and scale.

Prefer language such as "reported activity-weighted unit cost," "descriptive benchmark," and "pattern requiring further investigation" over evaluative claims.

Costs may reflect case mix, complexity, provider structure, reporting practices, or genuine service-delivery differences — not necessarily efficiency.

Architecture
text
NHS_Costs_Intelligence/
├── Dockerfile
├── .dockerignore
├── pytest.ini
├── requirements.txt
├── data/
│   └── processed/
│       ├── nhs_ncc_clean.csv        # committed source data
│       └── nhs_costs.duckdb          # gitignored; self-built on startup
├── src/
│   ├── load_database.py              # build_database()
│   └── database.py                   # get_connection(), read-only
├── dashboard/
│   ├── streamlit_app.py              # multi-page Streamlit app
│   └── queries.py                     # parameterised SQL query functions
├── Figures/                            # generated chart images
├── generate_figures.py                # produces the 5-figure descriptive set
├── scripts/
│   └── verify_csv.py                  # validates required columns before use
└── tests/
    ├── test_queries.py
    └── test_database_connection.py
Why DuckDB? It gives a real, parameterised SQL layer for an analytical dataset of this size without the operational overhead of running a separate database server — a good fit for a self-contained, reproducible portfolio deployment.

Why self-building on startup? The .duckdb file is gitignored. On first run, ensure_database_built() detects the file is missing and calls build_database() to construct it directly from the committed CSV, inside an atomic temp-file-then-rename step to avoid write conflicts if multiple app instances start simultaneously. This means the entire app is reproducible from source control alone.

Running Locally
bash
git clone <repo-url>
cd NHS_Costs_Intelligence
pip install -r requirements.txt
python scripts/verify_csv.py data/processed/nhs_ncc_clean.csv
streamlit run dashboard/streamlit_app.py
Running Tests
bash
pytest
Test configuration lives in pytest.ini (pythonpath = .) so src and dashboard resolve correctly as packages during test collection.

Running with Docker
bash
docker build -t nhs-costs-intelligence .
docker run -p 8501:8501 -e PORT=8501 nhs-costs-intelligence
Then open http://localhost:8501.

Deployment
Deployed as a containerised web service on Render, built from the repository's Dockerfile. The Streamlit app binds to Render's dynamically assigned $PORT and exposes Streamlit's built-in /_stcore/health endpoint for Render's health checks.

Limitations and Next Steps
NCCI's exact formula, denominator, and scale still require independent validation before any efficiency-adjacent use.

The 999 - Unknown department category and other data-quality flags (negative costs, extreme values, zero/negative NCCI) are excluded from valid_cost_records but retained in the full cost_records table for audit — they have not yet been individually investigated.

Planned additions: a provider drill-down page, a robust variation page using IQR, a dedicated data-quality review page, and an NCCI diagnostics page — all backed by query functions already implemented in queries.py.

An optional cautious baseline regression/tree model on unusual residuals is planned only after data definitions and quality checks are fully defensible — explicitly not intended to produce efficiency rankings.

Tech Stack
Python, Streamlit, DuckDB, Plotly, pandas, pytest, Docker, Render, GitHub Actions (CI, planned).

Author
Built as a CV-ready data science portfolio project by a final-year Computer Science / Data Science student based in London, UK.
