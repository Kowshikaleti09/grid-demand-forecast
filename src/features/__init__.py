"""Feature engineering layer.

Reads raw datasets from ``data/raw/``, joins demand with weather and
calendar covariates, and produces analysis-ready feature tables in
``data/processed/``.

Typical responsibilities:
- lag and rolling-window features for autoregressive signal,
- calendar features (hour-of-day, day-of-week, holidays),
- weather-derived features (heating/cooling degree hours),
- train/validation/test splitting utilities for time-series CV.

This package must be deterministic and side-effect-free aside from writes
to ``data/processed/`` so that feature tables are reproducible from raw.
"""
