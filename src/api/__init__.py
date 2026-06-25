"""HTTP API for serving forecasts.

Exposes the trained models behind a thin web layer (intended to be
implemented with FastAPI). Typical endpoints:

- ``GET /healthz``: liveness/readiness probe for orchestrators.
- ``GET /forecast``: returns the next-N-hour demand forecast for a region.
- ``GET /models``: lists currently deployed model versions and metadata.

The API layer is a transport boundary only: request parsing, auth, and
response shaping live here, while prediction logic is delegated to
``src.models``.
"""
