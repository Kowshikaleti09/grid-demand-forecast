"""Energy demand forecasting system.

Top-level package for the grid demand forecasting project. Subpackages own
distinct stages of the pipeline:

- ``ingestion``: pulls raw demand and weather data from external sources.
- ``features``: transforms raw data into model-ready feature tables.
- ``models``: trains, evaluates, and serves forecasting models.
- ``api``: exposes forecasts and model metadata over HTTP.
- ``monitoring``: tracks data quality and model performance in production.
"""
