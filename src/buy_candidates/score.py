"""Sector-relative composite scoring.

Composite = w_v*Value + w_q*Quality + w_m*Momentum + w_y*Yield,
where each component is the within-sector percentile rank (0-1).
ETFs are scored separately with their own logic (price momentum + AUM proxy).
"""

from __future__ import annotations

WEIGHTS = {"value": 0.35, "quality": 0.25, "momentum": 0.25, "yield": 0.15}

VALUE_METRICS = ("trailing_pe", "price_to_book", "fcf_yield")
QUALITY_METRICS = ("roe", "debt_to_equity")
MOMENTUM_METRICS = ("return_3m",)
YIELD_METRICS = ("dividend_yield",)


def score_stocks(fundamentals):
    """Return DataFrame sorted by composite desc, with score breakdown columns."""
    raise NotImplementedError


def score_etfs(fundamentals):
    """ETFs need a separate scoring path — most don't have P/E or ROE."""
    raise NotImplementedError
