# Grid Demand Forecast

Production-grade pipeline for forecasting short-term electricity demand on
U.S. grid balancing authorities. Pulls hourly demand from the EIA Open
Data API, joins weather and calendar covariates, and serves forecasts
over an HTTP API with monitoring for data and model quality.

## Layout

```
src/
  ingestion/    Pull raw demand + weather data into data/raw/
  features/    Build model-ready feature tables in data/processed/
  models/     Train, evaluate, and serve forecasting models
  api/       FastAPI service exposing forecasts
  monitoring/   Data-quality and model-performance checks
tests/       Unit and integration tests
notebooks/     Exploratory analysis (not for production code)
data/raw/      Raw ingested data (gitignored)
data/processed/  Feature tables (gitignored)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in EIA_API_KEY
```

## Data sources

- **Demand:** hourly electricity demand (type `"D"`) from the EIA Open Data
  API v2 `electricity/rto/region-data` endpoint.
- **Respondent code alias:** EIA labels the California ISO (commonly **CAISO**)
  with the respondent code **`CISO`**. Demand for CAISO is therefore ingested
  and partitioned under `balancing_authority=CISO`.

## Status

Scaffold only — no business logic implemented yet.
