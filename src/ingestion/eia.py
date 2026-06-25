"""Client for fetching hourly electricity demand from the EIA Open Data API v2.

This module ingests hourly demand (type "D") for a single US grid balancing
authority from the ``electricity/rto/region-data`` endpoint, parses the response
into a tidy DataFrame, and lands it as raw parquet under ``data/raw/``.

Only the standard project dependencies are used: ``requests`` (HTTP),
``pandas`` (parsing/IO), ``pyarrow`` (parquet engine), and ``python-dotenv``
(secret loading). Retry/backoff is hand-rolled to avoid an extra dependency.

Note on respondent codes: EIA identifies balancing authorities by short
respondent codes that do not always match their common names. In particular
``"CISO"`` is EIA's code for the California Independent System Operator,
commonly known as **CAISO** — so demand for CAISO lands under the partition
label ``balancing_authority=CISO``.
"""

from __future__ import annotations

import os
import random
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# Load secrets from a local .env (gitignored). The real EIA key never enters
# version control; only .env.example is tracked.
load_dotenv()
EIA_API_KEY: str | None = os.getenv("EIA_API_KEY")

# EIA v2 hourly region demand endpoint.
EIA_BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"

# The API returns at most this many rows per request; we page past it.
PAGE_LIMIT = 5000

# Where raw ingested parquet is written (gitignored).
RAW_DATA_DIR = Path("data/raw")

# Retry policy for transient HTTP failures.
MAX_RETRIES = 5
BACKOFF_BASE = 1.0  # seconds; grows exponentially per attempt
# HTTP statuses worth retrying: rate limiting + transient server errors.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Output schema, used as the single source of truth for column order/dtypes.
COLUMNS = ["timestamp_utc", "balancing_authority", "demand_mwh"]


def _request_with_retry(url: str, params: dict) -> dict:
    """GET ``url`` with exponential backoff on transient errors.

    Retries on connection-level failures and on retryable HTTP statuses
    (429 plus 5xx). Non-retryable 4xx responses (e.g. 400 bad request, 403
    invalid key) raise immediately so misconfiguration fails fast.

    Args:
        url: Fully-qualified endpoint URL.
        params: Query parameters (including the API key).

    Returns:
        The parsed ``response`` object from the EIA JSON envelope.

    Raises:
        requests.HTTPError: On a non-retryable status or after exhausting
            retries on a retryable status.
        requests.RequestException: On connection failures after exhausting
            retries.
    """
    last_exc: Exception | None = None

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            # Connection reset / timeout / DNS — transient, so back off and retry.
            last_exc = exc
        else:
            if resp.status_code not in RETRYABLE_STATUS:
                # Either a success or a hard client error; let raise_for_status
                # surface any non-2xx (no point retrying e.g. a bad API key).
                resp.raise_for_status()
                return resp.json()["response"]
            # Retryable status: remember it, then fall through to backoff.
            last_exc = requests.HTTPError(
                f"{resp.status_code} from EIA API", response=resp
            )
            # Honor a server-provided Retry-After (seconds) when present.
            retry_after = resp.headers.get("Retry-After")
            if retry_after is not None and retry_after.isdigit():
                time.sleep(int(retry_after))
                continue

        # Exponential backoff with jitter: base * 2**attempt + [0,1)s of jitter
        # spreads out retries and avoids thundering-herd retries against the API.
        if attempt < MAX_RETRIES - 1:
            time.sleep(BACKOFF_BASE * (2**attempt) + random.random())

    # All attempts failed — re-raise the most recent error for the caller.
    assert last_exc is not None
    raise last_exc


def fetch_demand(
    balancing_authority: str, start: date, end: date
) -> pd.DataFrame:
    """Fetch hourly demand for one balancing authority over ``[start, end]``.

    Calls the EIA v2 region-data endpoint for demand (type "D") at hourly
    frequency, paging over the API's 5000-row limit, and returns a tidy frame.

    Args:
        balancing_authority: EIA respondent code, e.g. ``"CAISO"``.
        start: First date to fetch (inclusive).
        end: Last date to fetch (inclusive).

    Returns:
        DataFrame with columns ``[timestamp_utc, balancing_authority,
        demand_mwh]`` sorted ascending by timestamp and deduplicated. Empty
        (but correctly typed) if the API returns no rows.

    Raises:
        RuntimeError: If ``EIA_API_KEY`` is not configured.
    """
    if not EIA_API_KEY:
        raise RuntimeError(
            "EIA_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    # EIA accepts hourly bounds as YYYY-MM-DDTHH. Cover the full end day (23:00).
    base_params = {
        "api_key": EIA_API_KEY,
        "frequency": "hourly",
        "data[0]": "value",
        "facets[respondent][]": balancing_authority,
        "facets[type][]": "D",  # D = Demand
        "start": start.strftime("%Y-%m-%dT00"),
        "end": end.strftime("%Y-%m-%dT23"),
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": PAGE_LIMIT,
    }

    rows: list[dict] = []
    offset = 0
    while True:
        # Pagination: the API caps each response at PAGE_LIMIT rows. We request
        # a page, then advance the offset by PAGE_LIMIT. We stop when the API
        # reports we've reached `total`, or returns a short/empty final page.
        params = {**base_params, "offset": offset}
        response = _request_with_retry(EIA_BASE_URL, params)

        page = response.get("data", [])
        rows.extend(page)

        total = int(response.get("total", 0))
        offset += PAGE_LIMIT
        if not page or offset >= total:
            break

    if not rows:
        # Return an empty frame with the right columns/dtypes for downstream code.
        return pd.DataFrame(
            {
                "timestamp_utc": pd.Series([], dtype="datetime64[ns, UTC]"),
                "balancing_authority": pd.Series([], dtype="object"),
                "demand_mwh": pd.Series([], dtype="float64"),
            }
        )

    raw = pd.DataFrame(rows)
    tidy = pd.DataFrame(
        {
            # EIA `period` values are UTC hour strings (e.g. "2024-01-01T05").
            "timestamp_utc": pd.to_datetime(raw["period"], utc=True),
            "balancing_authority": raw["respondent"],
            # Some hours can be null/missing; coerce to float so they become NaN.
            "demand_mwh": pd.to_numeric(raw["value"], errors="coerce"),
        }
    )

    # Sort causally and drop any duplicate hours the API may return at page seams.
    tidy = (
        tidy.sort_values("timestamp_utc")
        .drop_duplicates(subset="timestamp_utc")
        .reset_index(drop=True)
    )
    return tidy[COLUMNS]


def save_raw(df: pd.DataFrame, balancing_authority: str) -> list[Path]:
    """Write demand rows to ``data/raw/`` as date-partitioned parquet.

    Output layout is Hive-style so ``pd.read_parquet`` on the balancing-authority
    root auto-discovers partitions::

        data/raw/balancing_authority=<BA>/date=<YYYY-MM-DD>/demand.parquet

    The write is idempotent: each (BA, date) partition is written to a single
    fixed filename and overwritten on re-run, so re-ingesting a date range
    replaces partitions rather than accumulating duplicate files.

    Args:
        df: Frame as returned by :func:`fetch_demand`.
        balancing_authority: EIA respondent code used as the top-level partition.

    Returns:
        Sorted list of parquet file paths written (empty if ``df`` is empty).
    """
    if df.empty:
        return []

    written: list[Path] = []
    # Partition by calendar date (UTC) for incremental, queryable storage.
    partition_dates = df["timestamp_utc"].dt.date
    for day, group in df.groupby(partition_dates):
        partition_dir = (
            RAW_DATA_DIR
            / f"balancing_authority={balancing_authority}"
            / f"date={day.isoformat()}"
        )
        partition_dir.mkdir(parents=True, exist_ok=True)

        out_path = partition_dir / "demand.parquet"
        # Single fixed filename per partition -> overwrite makes re-runs idempotent.
        group.reset_index(drop=True).to_parquet(
            out_path, engine="pyarrow", index=False
        )
        written.append(out_path)

    return sorted(written)


if __name__ == "__main__":
    # Fetch the last 90 days of CAISO demand and land it as raw parquet.
    # NB: "CISO" is EIA's respondent code for the California ISO (CAISO).
    ca_iso = "CISO"
    end_date = date.today()
    start_date = end_date - timedelta(days=90)

    demand = fetch_demand(ca_iso, start_date, end_date)
    paths = save_raw(demand, ca_iso)

    print(
        f"Fetched {len(demand)} rows of {ca_iso} demand "
        f"({start_date} to {end_date}); wrote {len(paths)} partition file(s)."
    )
