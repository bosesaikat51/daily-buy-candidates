"""Fetch fundamentals + prices from yfinance with on-disk parquet cache.

Batches requests, retries on rate limits, skips tickers with bad data.
Cache key: (ticker, date) — one parquet per ticker, refreshed on weekday.
"""

from __future__ import annotations

from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"


def fetch_fundamentals(tickers: list[str]):
    """Return a pandas DataFrame keyed by ticker with columns:

    sector, trailing_pe, price_to_book, fcf_yield, roe, debt_to_equity,
    return_3m, dividend_yield, last_close, currency.
    """
    raise NotImplementedError
