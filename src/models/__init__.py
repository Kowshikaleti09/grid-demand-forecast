"""Forecasting models.

Houses training, evaluation, and inference code for demand forecasting
models (baselines such as seasonal-naive and ARIMA, plus ML models such as
gradient-boosted trees and sequence models).

Each model should expose a consistent ``fit`` / ``predict`` interface so
that training pipelines, backtests, and the serving API can swap
implementations without code changes elsewhere. Serialized model artifacts
and metadata belong in a model registry (path/URI configured per
environment), not inside this package.
"""
