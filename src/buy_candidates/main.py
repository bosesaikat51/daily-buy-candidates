"""Daily buy-candidates pipeline orchestrator.

universe -> data -> score -> sector medians -> headlines ->
narrate (picks + macro + synthesis) -> archive -> render.

CLI:
    uv run python -m buy_candidates.main                # full universe
    uv run python -m buy_candidates.main --limit 200    # first 200 tickers (fast local iteration)
"""

from __future__ import annotations

import argparse
import logging
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

from buy_candidates.archive import save_daily
from buy_candidates.data import fetch_fundamentals
from buy_candidates.narrate import narrate_macro, narrate_pick, narrate_synthesis
from buy_candidates.news import macro_headlines, ticker_headlines
from buy_candidates.render import render_dashboard
from buy_candidates.score import score_etfs, score_stocks
from buy_candidates.universe import load_universe

REPO_ROOT = Path(__file__).resolve().parents[2]
TOP_N_STOCKS = 10
TOP_N_ETFS = 3
TICKER_HEADLINE_LIMIT = 5
MACRO_HEADLINE_LIMIT = 12

log = logging.getLogger(__name__)


def _sector_medians(fundamentals: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Per-sector median of every numeric metric. Used for narration comparatives."""
    numeric = fundamentals.select_dtypes(include="number")
    if numeric.empty or "sector" not in fundamentals.columns:
        return {}
    grouped = fundamentals[["sector", *numeric.columns]].groupby("sector").median(numeric_only=True)
    return {
        sector: {k: (v if pd.notna(v) else None) for k, v in row.items()}
        for sector, row in grouped.to_dict(orient="index").items()
    }


def _build_pick(
    ticker: str,
    score_row: pd.Series,
    universe_meta_by_ticker: dict[str, dict],
    sector_medians: dict[str, dict],
) -> dict:
    """Assemble the cross-module pick payload (used by narrate + render + archive)."""
    sector = score_row.get("sector")
    meta = universe_meta_by_ticker.get(ticker, {})

    def _val(col: str):
        v = score_row.get(col)
        return None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)

    raw_metrics = {
        "trailing_pe": _val("trailing_pe"),
        "price_to_book": _val("price_to_book"),
        "fcf_yield": _val("fcf_yield"),
        "roe": _val("roe"),
        "debt_to_equity": _val("debt_to_equity"),
        "return_3m": _val("return_3m"),
        "dividend_yield": _val("dividend_yield"),
    }
    scores = {
        "value": _val("score_value"),
        "quality": _val("score_quality"),
        "momentum": _val("score_momentum"),
        "yield": _val("score_yield"),
    }
    return {
        "ticker": ticker,
        "name": meta.get("name") or ticker,
        "region": meta.get("region"),
        "sector": sector,
        "currency": _val("currency"),
        "last_close": _val("last_close"),
        "composite": _val("composite"),
        "raw_metrics": raw_metrics,
        "scores": scores,
        "sector_medians": sector_medians.get(sector, {}),
        "headlines": [],
        "narrative": None,
    }


def _composition_stats(picks: list[dict]) -> dict:
    if not picks:
        return {"n_picks": 0}
    sectors = Counter(p["sector"] for p in picks if p.get("sector"))
    regions = Counter(p["region"] or "—" for p in picks)
    comp_scores = [p["composite"] for p in picks if p.get("composite") is not None]

    def _safe_mean(key: str) -> float | None:
        vals = [p["scores"].get(key) for p in picks if p.get("scores")]
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    return {
        "n_picks": len(picks),
        "sector_breakdown": dict(sectors.most_common()),
        "region_breakdown": dict(regions.most_common()),
        "avg_component_scores": {
            "value": _safe_mean("value"),
            "quality": _safe_mean("quality"),
            "momentum": _safe_mean("momentum"),
            "yield": _safe_mean("yield"),
        },
        "composite_range": [round(min(comp_scores), 1), round(max(comp_scores), 1)] if comp_scores else None,
    }


def _missing_sectors(top_picks: list[dict], all_stocks: pd.DataFrame) -> list[str]:
    """Sectors with ≥10 universe members that have zero representation in top picks."""
    if all_stocks.empty:
        return []
    sector_counts = all_stocks["sector"].value_counts(dropna=True)
    present = {p["sector"] for p in top_picks}
    return [s for s, n in sector_counts.items() if n >= 10 and s not in present]


def run(limit: int | None = None) -> Path:
    load_dotenv(REPO_ROOT / ".env")

    log.info("loading universe...")
    universe_rows = load_universe()
    if limit is not None:
        universe_rows = universe_rows[:limit]
        log.info("universe limited to first %d tickers (local iteration)", limit)
    tickers = [r["ticker"] for r in universe_rows]
    universe_meta_by_ticker = {r["ticker"]: r for r in universe_rows}
    log.info("universe: %d tickers", len(tickers))

    log.info("fetching fundamentals...")
    fundamentals = fetch_fundamentals(tickers)
    log.info("fundamentals: %d rows", len(fundamentals))

    log.info("scoring stocks + ETFs...")
    ranked_stocks = score_stocks(fundamentals)
    ranked_etfs = score_etfs(fundamentals)
    log.info("ranked %d stocks, %d ETFs", len(ranked_stocks), len(ranked_etfs))

    sector_medians = _sector_medians(fundamentals)

    top_stocks_df = ranked_stocks.head(TOP_N_STOCKS)
    top_etfs_df = ranked_etfs.head(TOP_N_ETFS)

    stock_picks = [
        _build_pick(t, row, universe_meta_by_ticker, sector_medians)
        for t, row in top_stocks_df.iterrows()
    ]
    etf_picks = [
        _build_pick(t, row, universe_meta_by_ticker, sector_medians)
        for t, row in top_etfs_df.iterrows()
    ]

    # A BOM or stray whitespace in the env var blows up httpx at
    # header-encode time — see daily log 2026-05-21.
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip().lstrip("﻿")
    client = Anthropic(api_key=api_key)

    log.info("fetching headlines + narrating %d stock picks...", len(stock_picks))
    for pick in stock_picks:
        pick["headlines"] = ticker_headlines(pick["ticker"], limit=TICKER_HEADLINE_LIMIT)
        try:
            pick["narrative"] = narrate_pick(client, pick, pick["headlines"])
        except Exception as e:  # noqa: BLE001
            log.warning("narrate_pick failed for %s: %s", pick["ticker"], e)
            pick["narrative"] = "Narration unavailable for today's run."

    # ETFs: lighter touch — skip per-pick LLM narration for now, just list them.
    for pick in etf_picks:
        pick["headlines"] = ticker_headlines(pick["ticker"], limit=TICKER_HEADLINE_LIMIT)
        pick["narrative"] = (
            f"Ranked on momentum + yield (no sector fundamentals for ETFs). "
            f"3M return {pick['raw_metrics'].get('return_3m', 0):+.1%} · "
            f"yield rank {(pick['scores'].get('yield') or 0):.0f}/100."
        )

    log.info("narrating macro context...")
    macro = macro_headlines(limit=MACRO_HEADLINE_LIMIT)
    macro_blurb = narrate_macro(client, macro)

    log.info("computing composition stats + synthesis...")
    composition = _composition_stats(stock_picks)
    universe_meta = {
        "n_screened": len(tickers),
        "n_scored_stocks": len(ranked_stocks),
        "n_scored_etfs": len(ranked_etfs),
        "missing_sectors": _missing_sectors(stock_picks, ranked_stocks),
    }
    synthesis = narrate_synthesis(client, stock_picks, composition, macro_blurb, universe_meta)

    as_of = datetime.now(tz=timezone.utc)

    log.info("archiving snapshot...")
    save_daily(
        as_of=as_of.date(),
        stock_picks=stock_picks,
        etf_picks=etf_picks,
        macro_blurb=macro_blurb,
        synthesis=synthesis,
        composition=composition,
        universe_meta=universe_meta,
    )

    log.info("rendering dashboard...")
    out_path = render_dashboard(
        stock_picks=stock_picks,
        etf_picks=etf_picks,
        macro_blurb=macro_blurb,
        synthesis=synthesis,
        composition=composition,
        universe_meta=universe_meta,
        as_of=as_of,
    )
    log.info("done — dashboard at %s", out_path)
    return out_path


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Run the daily buy-candidates pipeline.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the universe to the first N tickers (for local iteration).",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    run(limit=args.limit)


if __name__ == "__main__":
    _cli()
