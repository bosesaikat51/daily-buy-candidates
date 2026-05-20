"""Sector-relative composite scoring.

Composite = w_v*Value + w_q*Quality + w_m*Momentum + w_y*Yield,
where each component is the within-sector percentile rank (0-100).
ETFs are scored separately on momentum + yield only — no sector to rank within.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WEIGHTS = {"value": 0.35, "quality": 0.25, "momentum": 0.25, "yield": 0.15}

# (column, higher_is_better) — drives the rank direction in _pct_within.
_VALUE = [("trailing_pe", False), ("price_to_book", False), ("fcf_yield", True)]
_QUALITY = [("roe", True), ("debt_to_equity", False)]
_MOMENTUM = [("return_3m", True)]
_YIELD = [("dividend_yield", True)]

_CORE_METRICS = [m for m, _ in _VALUE + _QUALITY + _MOMENTUM + _YIELD]
_MIN_NON_NULL_CORE = 4


def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """Null out values where the metric is conceptually meaningless.

    Negative earnings make trailing P/E uninterpretable; negative book value
    does the same for P/B; negative equity does the same for D/E.
    """
    out = df.copy()
    out.loc[out["trailing_pe"].le(0), "trailing_pe"] = np.nan
    out.loc[out["price_to_book"].le(0), "price_to_book"] = np.nan
    out.loc[out["debt_to_equity"].lt(0), "debt_to_equity"] = np.nan
    return out


def _pct_within(
    df: pd.DataFrame, group_col: str | None, col: str, higher_better: bool
) -> pd.Series:
    """Percentile rank (0-100) within `group_col`, NaN-preserving."""
    ascending = higher_better
    if group_col is None:
        return df[col].rank(pct=True, ascending=ascending) * 100
    return df.groupby(group_col, dropna=False)[col].transform(
        lambda s: s.rank(pct=True, ascending=ascending) * 100
    )


def _component(
    df: pd.DataFrame, metrics: list[tuple[str, bool]], group_col: str | None
) -> pd.Series:
    """Mean of per-metric percentiles. Skips NaN — if all metrics missing, NaN."""
    parts = [_pct_within(df, group_col, col, hb) for col, hb in metrics]
    return pd.concat(parts, axis=1).mean(axis=1)


def _composite(components: dict[str, pd.Series]) -> pd.Series:
    """Weighted mean of components, renormalized over the non-NaN ones per row."""
    comp_df = pd.DataFrame(components)
    weights = pd.Series(WEIGHTS)[comp_df.columns]
    num = comp_df.fillna(0).mul(weights, axis=1).sum(axis=1)
    denom = comp_df.notna().mul(weights, axis=1).sum(axis=1)
    return (num / denom).where(denom > 0)


def score_stocks(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Return stocks (rows with a non-null `sector`) scored and ranked.

    Adds columns: score_value, score_quality, score_momentum, score_yield,
    composite. Sorted by composite desc. Rows with fewer than
    ``_MIN_NON_NULL_CORE`` non-NaN core metrics are dropped.
    """
    stocks = fundamentals[fundamentals["sector"].notna()].copy()
    if stocks.empty:
        return stocks

    stocks = _sanitize(stocks)

    enough_data = stocks[_CORE_METRICS].notna().sum(axis=1) >= _MIN_NON_NULL_CORE
    stocks = stocks.loc[enough_data].copy()
    if stocks.empty:
        return stocks

    components = {
        "value": _component(stocks, _VALUE, "sector"),
        "quality": _component(stocks, _QUALITY, "sector"),
        "momentum": _component(stocks, _MOMENTUM, "sector"),
        "yield": _component(stocks, _YIELD, "sector"),
    }
    for name, s in components.items():
        stocks[f"score_{name}"] = s
    stocks["composite"] = _composite(components)
    stocks = stocks.dropna(subset=["composite"])

    return stocks.sort_values("composite", ascending=False)


def score_etfs(fundamentals: pd.DataFrame) -> pd.DataFrame:
    """Score ETFs on momentum + yield only — most have no sector / no fundamentals.

    ETFs are identified as rows with null `sector`. Ranked globally across the
    ETF set (no sector buckets). Returns sorted by composite desc.
    """
    etfs = fundamentals[fundamentals["sector"].isna()].copy()
    if etfs.empty:
        return etfs

    components = {
        "momentum": _component(etfs, _MOMENTUM, None),
        "yield": _component(etfs, _YIELD, None),
    }
    for name, s in components.items():
        etfs[f"score_{name}"] = s
    etfs["composite"] = _composite(components)
    etfs = etfs.dropna(subset=["composite"])

    return etfs.sort_values("composite", ascending=False)


if __name__ == "__main__":
    import logging

    from buy_candidates.data import fetch_fundamentals

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    sample = [
        "AAPL", "MSFT", "GOOGL", "NVDA", "META",
        "JPM", "BAC", "GS", "MS", "WFC",
        "SAP.DE", "ASML.AS", "NESN.SW", "VOD.L",
        "VWCE.DE", "EQQQ.DE",
    ]
    df = fetch_fundamentals(sample)

    cols_stocks = ["sector", "composite", "score_value", "score_quality", "score_momentum", "score_yield"]
    cols_etfs = ["composite", "score_momentum", "score_yield"]

    print("\n== Stocks ==")
    print(score_stocks(df)[cols_stocks].round(1).to_string())
    print("\n== ETFs ==")
    print(score_etfs(df)[cols_etfs].round(1).to_string())
