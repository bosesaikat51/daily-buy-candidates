"""Render dashboard.html.j2 -> docs/index.html.

Formatting helpers (percent strings, ratio strings, tone classes) are
intentionally simple — they live with rendering, not with scoring or
narration, so swapping the template doesn't touch the rest of the pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "templates"
OUTPUT_DIR = REPO_ROOT / "docs"

log = logging.getLogger(__name__)


def _fmt_pct(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{v * 100:+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct_plain(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{v * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_ratio(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.1f}×"
    except (TypeError, ValueError):
        return "—"


def _fmt_price(v, currency: str | None) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _tone(value, *, high_good: bool) -> str:
    """Return 'pos'/'neg'/'' for the metric tone class."""
    if value is None:
        return ""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if high_good:
        if v > 0:
            return "pos"
        if v < 0:
            return "neg"
        return ""
    if v < 0:
        return "neg"
    return ""


def _exchange_label(ticker: str, region: str | None) -> str:
    if "." not in ticker:
        return "NYSE / NASDAQ" if region == "US" else (region or "")
    suffix = ticker.rsplit(".", 1)[-1].upper()
    return {
        "L": "LSE",
        "DE": "Xetra",
        "PA": "Euronext Paris",
        "SW": "SIX",
        "AS": "Euronext Amsterdam",
        "MI": "Borsa Italiana",
        "MC": "BME",
        "ST": "Nasdaq Stockholm",
        "CO": "Nasdaq Copenhagen",
        "OL": "Oslo",
        "HE": "Nasdaq Helsinki",
        "BR": "Euronext Brussels",
        "VI": "Wiener Börse",
        "IR": "Euronext Dublin",
        "LS": "Euronext Lisbon",
        "WA": "GPW",
    }.get(suffix, suffix)


def _build_display_metrics(raw: dict) -> list[dict]:
    """List of {label, value, tone} for the pick card's metrics grid."""
    return [
        {"label": "P/E", "value": _fmt_ratio(raw.get("trailing_pe")), "tone": ""},
        {"label": "P/B", "value": _fmt_ratio(raw.get("price_to_book")), "tone": ""},
        {"label": "ROE", "value": _fmt_pct_plain(raw.get("roe")), "tone": _tone(raw.get("roe"), high_good=True)},
        {"label": "Div yld", "value": _fmt_pct_plain(raw.get("dividend_yield_pct") or raw.get("dividend_yield")), "tone": ""},
        {"label": "FCF yld", "value": _fmt_pct_plain(raw.get("fcf_yield")), "tone": _tone(raw.get("fcf_yield"), high_good=True)},
        {"label": "3M", "value": _fmt_pct(raw.get("return_3m")), "tone": _tone(raw.get("return_3m"), high_good=True)},
        {"label": "D/E", "value": f"{float(raw['debt_to_equity']):.0f}" if raw.get("debt_to_equity") is not None else "—", "tone": ""},
        {"label": "Score", "value": f"{raw.get('composite', 0):.0f}", "tone": ""},
    ]


def _pick_for_template(p: dict) -> dict:
    """Map a pipeline pick into the shape the Jinja template expects."""
    raw = dict(p.get("raw_metrics") or {})
    raw["composite"] = p.get("composite")
    chg = p.get("raw_metrics", {}).get("return_3m")
    chg_tone = _tone(chg, high_good=True)
    return {
        "ticker": p["ticker"],
        "name": p.get("name") or p["ticker"],
        "sector": p.get("sector") or "—",
        "currency": p.get("currency") or "",
        "composite": f"{p['composite']:.0f}",
        "scores": {k: int(round(v)) if v is not None else 0 for k, v in (p.get("scores") or {}).items()},
        "narrative": p.get("narrative") or "—",
        "metrics": _build_display_metrics(raw),
        "last_close": _fmt_price(p.get("last_close"), p.get("currency")),
        "chg": _fmt_pct(chg) if chg is not None else "",
        "chg_tone": chg_tone,
        "exchange": _exchange_label(p["ticker"], p.get("region")),
    }


def _summarize_composition(composition: dict, universe_meta: dict) -> str:
    sectors = composition.get("sector_breakdown") or {}
    regions = composition.get("region_breakdown") or {}
    n_picks = composition.get("n_picks", 0)
    n_universe = universe_meta.get("n_screened", 0)
    top_sector = next(iter(sectors), None)
    region_str = " · ".join(f"{r} {c}" for r, c in regions.items())
    tilt = composition.get("avg_component_scores") or {}
    tilt_order = sorted(tilt.items(), key=lambda kv: kv[1] or 0, reverse=True)
    dominant_tilt = tilt_order[0][0].title() if tilt_order else "—"
    return (
        f"{n_picks} picks · screened {n_universe} tickers · "
        f"top sector: {top_sector or '—'} · "
        f"regions: {region_str or '—'} · "
        f"dominant tilt: {dominant_tilt}"
    )


def _hero_headline(composition: dict) -> str:
    """A one-liner derived from the composition stats for the hero h1."""
    sectors = composition.get("sector_breakdown") or {}
    if not sectors:
        return "Today's ranked screen"
    top_sector, top_count = next(iter(sectors.items()))
    n = composition.get("n_picks", 0)
    if top_count >= max(3, n // 2):
        return f"{top_sector} leads today's screen"
    return "Today's ranked screen"


def render_dashboard(
    stock_picks: list[dict],
    etf_picks: list[dict],
    macro_blurb: str,
    synthesis: str,
    composition: dict,
    universe_meta: dict,
    as_of: datetime,
) -> Path:
    """Render templates/dashboard.html.j2 → docs/index.html. Returns output path."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("dashboard.html.j2")

    pick_groups: list[dict] = []
    if stock_picks:
        pick_groups.append(
            {
                "title": "Stocks",
                "meta": f"{len(stock_picks)} ranked",
                "picks": [_pick_for_template(p) for p in stock_picks],
            }
        )
    if etf_picks:
        pick_groups.append(
            {
                "title": "ETFs",
                "meta": f"{len(etf_picks)} ranked · momentum + yield only",
                "picks": [_pick_for_template(p) for p in etf_picks],
            }
        )

    html = template.render(
        as_of=as_of,
        hero_headline=_hero_headline(composition),
        synthesis_paragraphs=[p.strip() for p in synthesis.split("\n\n") if p.strip()],
        composition_summary=_summarize_composition(composition, universe_meta),
        macro_blurb=macro_blurb,
        pick_groups=pick_groups,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    log.info("rendered dashboard to %s", out_path)
    return out_path


def render_past_picks() -> None:
    """Render docs/past_picks.html by reading archive/*.json. Deferred."""
    raise NotImplementedError("past_picks deferred until we have ≥7 archive days")
