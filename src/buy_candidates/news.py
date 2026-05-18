"""News fetching: per-ticker (yfinance) + macro (Reuters / FT RSS)."""

from __future__ import annotations

MACRO_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://www.ft.com/markets?format=rss",
    "https://www.handelsblatt.com/contentexport/feed/schlagzeilen",
]


def ticker_headlines(ticker: str, limit: int = 5) -> list[dict]:
    """Recent headlines for one ticker — [{title, url, published}, ...]."""
    raise NotImplementedError


def macro_headlines(limit: int = 10) -> list[dict]:
    """Today's top macro / geopolitics headlines across MACRO_FEEDS."""
    raise NotImplementedError
