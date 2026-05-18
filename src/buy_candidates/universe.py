"""Load the screening universe: S&P 500 + STOXX 600 + curated ETFs."""

from __future__ import annotations

from pathlib import Path

UNIVERSE_FILE = Path(__file__).resolve().parents[2] / "data" / "universe.yaml"


def load_universe() -> list[dict]:
    """Return [{ticker, name, asset_class, region, sector?}, ...].

    Stocks: scraped from Wikipedia S&P 500 and STOXX 600 constituent tables.
    ETFs: read from the curated list in data/universe.yaml.
    Tickers in `excluded_tickers` are skipped.
    """
    raise NotImplementedError
