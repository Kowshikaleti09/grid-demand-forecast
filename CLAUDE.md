# Grid Demand Forecast — Project Conventions

## What this project is
A production-style system that forecasts short-term electricity demand for a
US grid balancing authority. It ingests hourly demand (EIA Open Data API) and
weather covariates, engineers features, trains and evaluates forecasting
models, serves predictions over a FastAPI service, and monitors data and model
quality. Built incrementally as a portfolio project.

## Code standards
- Python 3.12. Functions and methods have type hints and concise docstrings.
- Prefer small, focused modules over large catch-all files.
- Source code lives under `src/` in the existing subpackages: ingestion,
  features, models, api, monitoring.
- Exploratory work goes in `notebooks/`; never import notebooks into `src/`.
- Tests go in `tests/` using pytest.

## Data rules
- Never commit data. `data/raw/` and `data/processed/` are gitignored.
- Never commit secrets. The real key lives in `.env` (gitignored); only
  `.env.example` is tracked.
- Raw ingested data is written to `data/raw/` as parquet; feature tables to
  `data/processed/`.

## Time-series discipline (important)
- No lookahead leakage: features at time t may only use information available
  at or before t. Lag and rolling features must be computed causally.
- Validation uses time-ordered splits (blocked / expanding-window CV), never
  random k-fold.

## Working style
- Implement one module or concern at a time; keep changes reviewable.
- Explain non-obvious design decisions in code comments or docstrings.
- When choosing between approaches, prefer the simpler one and note the
  tradeoff rather than over-engineering.
