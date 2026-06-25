"""Data ingestion layer.

Responsible for fetching raw input data from external providers (e.g. the
U.S. EIA Open Data API for hourly demand, NOAA / weather APIs for
temperature and humidity covariates) and landing it in ``data/raw/`` in a
consistent, append-friendly format (parquet partitioned by date).

Modules here should encapsulate API clients, retry/backoff policies, and
schema validation for raw payloads. They must remain side-effect-only with
respect to ``data/raw/`` — no feature engineering happens at this stage.
"""
