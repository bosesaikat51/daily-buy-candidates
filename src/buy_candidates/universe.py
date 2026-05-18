"""Load the screening universe: S&P 500 + STOXX 600 + curated ETFs."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd
import requests
import yaml

UNIVERSE_FILE = Path(__file__).resolve().parents[2] / "data" / "universe.yaml"

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
STOXX600_URL = "https://en.wikipedia.org/wiki/STOXX_Europe_600"

USER_AGENT = (
    "daily-buy-candidates/0.1 "
    "(https://github.com/bosesaikat51/daily-buy-candidates)"
)

# STOXX 600 country -> yfinance exchange suffix.
# Tickers on the Wikipedia page are bare; yfinance needs the suffix.
COUNTRY_SUFFIX = {
    "United Kingdom": ".L",
    "Germany": ".DE",
    "France": ".PA",
    "Switzerland": ".SW",
    "Netherlands": ".AS",
    "Italy": ".MI",
    "Spain": ".MC",
    "Sweden": ".ST",
    "Denmark": ".CO",
    "Norway": ".OL",
    "Finland": ".HE",
    "Belgium": ".BR",
    "Austria": ".VI",
    "Ireland": ".IR",
    "Portugal": ".LS",
    "Poland": ".WA",
    "Luxembourg": ".LU",
    "Czech Republic": ".PR",
    "Hungary": ".BD",
    "Greece": ".AT",
}

log = logging.getLogger(__name__)


def _fetch_html(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def _scrape_sp500() -> list[dict]:
    tables = pd.read_html(io.StringIO(_fetch_html(SP500_URL)))
    df = tables[0]
    out: list[dict] = []
    for _, row in df.iterrows():
        # yfinance uses "-" not "." for class shares (BRK.B -> BRK-B)
        ticker = str(row["Symbol"]).strip().replace(".", "-")
        out.append(
            {
                "ticker": ticker,
                "name": str(row["Security"]).strip(),
                "asset_class": "stock",
                "region": "US",
                "sector": str(row["GICS Sector"]).strip(),
            }
        )
    return out


def _scrape_stoxx600() -> list[dict]:
    tables = pd.read_html(io.StringIO(_fetch_html(STOXX600_URL)))
    # The constituents table is the one with the "Ticker" and "Country" columns.
    df = next(
        (t for t in tables if {"Ticker", "Country"}.issubset(t.columns)),
        None,
    )
    if df is None:
        raise RuntimeError("STOXX 600 constituents table not found on Wikipedia page")
    out: list[dict] = []
    missing_suffix: set[str] = set()
    for _, row in df.iterrows():
        country = str(row["Country"]).strip()
        suffix = COUNTRY_SUFFIX.get(country)
        if suffix is None:
            missing_suffix.add(country)
            continue
        base = str(row["Ticker"]).strip()
        out.append(
            {
                "ticker": f"{base}{suffix}",
                "name": str(row["Company"]).strip(),
                "asset_class": "stock",
                "region": "EU",
                "sector": str(row["ICB Sector"]).strip(),
            }
        )
    if missing_suffix:
        log.warning("STOXX600: dropped countries with no yfinance suffix: %s", sorted(missing_suffix))
    return out


def _load_etfs(yaml_data: dict) -> list[dict]:
    return [
        {
            "ticker": e["ticker"],
            "name": e["name"],
            "asset_class": e.get("asset_class", "ETF"),
            "region": e.get("region"),
            "sector": e.get("sector"),
        }
        for e in (yaml_data.get("etfs") or [])
    ]


def load_universe() -> list[dict]:
    """Return [{ticker, name, asset_class, region, sector?}, ...].

    Stocks: scraped from Wikipedia S&P 500 and STOXX 600 constituent tables.
    ETFs: read from the curated list in data/universe.yaml.
    Tickers in `excluded_tickers` are skipped.
    """
    with UNIVERSE_FILE.open("r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f) or {}

    excluded = {str(t).strip() for t in (yaml_data.get("excluded_tickers") or [])}

    rows = _scrape_sp500() + _scrape_stoxx600() + _load_etfs(yaml_data)
    rows = [r for r in rows if r["ticker"] not in excluded]
    # De-duplicate by ticker, keep first occurrence.
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in rows:
        if r["ticker"] in seen:
            continue
        seen.add(r["ticker"])
        deduped.append(r)
    return deduped


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    rows = load_universe()
    by_region: dict[str, int] = {}
    for r in rows:
        by_region[r["region"] or "?"] = by_region.get(r["region"] or "?", 0) + 1
    print(f"Total: {len(rows)}  Breakdown: {by_region}")
    print("Sample:")
    for r in rows[:3] + rows[len(rows) // 2 : len(rows) // 2 + 3] + rows[-3:]:
        print(f"  {r['ticker']:12} {r['region']:3} {r['asset_class']:6} {r['sector'] or '-':20} {r['name']}")
