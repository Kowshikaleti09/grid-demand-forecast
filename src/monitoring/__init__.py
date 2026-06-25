"""Production monitoring.

Tracks the health of both data pipelines and deployed models:

- data-quality checks on ingested batches (schema drift, freshness,
  null/outlier rates),
- model-performance metrics computed against realized demand (MAPE, RMSE,
  pinball loss for quantile forecasts),
- drift detection on input feature distributions,
- alerting hooks (log, metrics endpoint, or webhook) so operators are
  paged on regressions.

Modules here should be safe to run on a schedule against production data
without mutating model artifacts or feature tables.
"""
