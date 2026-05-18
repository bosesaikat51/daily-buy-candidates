"""Fetch fundamentals + prices from yfinance with on-disk parquet cache.

Batches price requests, calls ``.info`` per ticker, caches per ticker per day,
and skips tickers whose ``.info`` blows up.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[2] / "cache"

COLUMNS = [
    "sector",
    "trailing_pe",
    "price_to_book",
    "fcf_yield",
    "roe",
    "debt_to_equity",
    "return_3m",
    "dividend_yield",
    "last_close",
    "currency",
]

log = logging.getLogger(__name__)


def _cache_path(ticker: str, d: date) -> Path:
    return CACHE_DIR / f"{ticker}_{d.strftime('%Y%m%d')}.parquet"


def _close_series(prices: pd.DataFrame, ticker: str) -> pd.Series:
    """Pull the Close series for one ticker out of a yf.download result.

    yf.download returns a MultiIndex frame when multiple tickers were requested
    and a flat frame for a single ticker — handle both.
    """
    if isinstance(prices.columns, pd.MultiIndex):
        if ticker in prices.columns.get_level_values(0):
            return prices[ticker]["Close"].dropna()
        return pd.Series(dtype=float)
    return prices["Close"].dropna() if "Close" in prices.columns else pd.Series(dtype=float)


def _build_row(ticker: str, prices: pd.DataFrame) -> dict | None:
    """Build the row dict for one ticker. Returns None on yfinance failure."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:  # noqa: BLE001 — yfinance raises a wide net
        log.warning("yfinance .info failed for %s: %s", ticker, e)
        return None

    mc = info.get("marketCap")
    fcf = info.get("freeCashflow")
    fcf_yield = (fcf / mc) if (fcf and mc) else None

    closes = _close_series(prices, ticker)
    if len(closes) >= 2:
        last_close = float(closes.iloc[-1])
        return_3m = float(last_close / closes.iloc[0] - 1.0)
    else:
        last_close = None
        return_3m = None

    return {
        "sector": info.get("sector"),
        "trailing_pe": info.get("trailingPE"),
        "price_to_book": info.get("priceToBook"),
        "fcf_yield": fcf_yield,
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "return_3m": return_3m,
        "dividend_yield": info.get("dividendYield"),
        "last_close": last_close,
        "currency": info.get("currency"),
    }


def fetch_fundamentals(tickers: list[str]) -> pd.DataFrame:
    """Return a pandas DataFrame keyed by ticker with columns:

    sector, trailing_pe, price_to_book, fcf_yield, roe, debt_to_equity,
    return_3m, dividend_yield, last_close, currency.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()

    rows: dict[str, dict] = {}
    to_fetch: list[str] = []
    for t in tickers:
        cp = _cache_path(t, today)
        if cp.exists():
            try:
                rows[t] = pd.read_parquet(cp).iloc[0].to_dict()
                continue
            except Exception as e:  # noqa: BLE001
                log.warning("cache read failed for %s: %s — refetching", t, e)
        to_fetch.append(t)

    log.info("fundamentals: %d cached, %d to fetch", len(rows), len(to_fetch))

    if to_fetch:
        log.info("downloading 3m price history for %d tickers", len(to_fetch))
        prices = yf.download(
            to_fetch,
            period="3mo",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )

        for i, t in enumerate(to_fetch, start=1):
            if i % 50 == 0:
                log.info("fundamentals: %d/%d fetched", i, len(to_fetch))
            row = _build_row(t, prices)
            if row is None:
                continue
            rows[t] = row
            pd.DataFrame([row], index=[t]).to_parquet(_cache_path(t, today))

    if not rows:
        return pd.DataFrame(columns=COLUMNS)

    df = pd.DataFrame.from_dict(rows, orient="index")[COLUMNS]
    df.index.name = "ticker"
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    sample = ["AAPL", "MSFT", "SAP.DE", "ASML.AS", "NESN.SW", "VOD.L", "VWCE.DE"]
    df = fetch_fundamentals(sample)
    print(df.to_string())
