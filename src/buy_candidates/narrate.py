"""Claude narration of quant-selected picks.

Uses claude-opus-4-7 for quality. Prompt caching applied to the SYSTEM_PROMPT so
the persona + format spec is cached across all picks within a run (the cache
TTL is 5 minutes — long enough to cover a full daily run of ~10 picks).

Anti-hallucination guardrails:
- Claude never invents a buy — it only narrates picks the screener surfaced.
- Claude must use ONLY the numbers in the input payload (raw metrics, sector
  percentiles, sector medians). The "never invent numbers" instruction is in
  the system prompt and reinforced by passing structured JSON input.
"""

from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """You are a sober equity analyst writing for an experienced
retail investor in Berlin who trades US and EU markets.

For each pick you receive, you get a structured JSON payload containing:
- ticker, name, sector, currency, last_close
- metrics: raw fundamentals (trailing_pe, price_to_book, fcf_yield, roe,
  debt_to_equity, return_3m, dividend_yield)
- percentiles: sector-relative rank 0-100 for each component (value, quality,
  momentum, yield) — higher = better within the sector
- sector_medians: the sector's median for the key metrics, so you can write
  comparative phrases like "trades at 8x earnings vs sector median 22x"
- headlines: recent ticker-specific news (title + publisher)

Write 2-3 tight sentences, in this order:

1. **What stands out in the data.** Cite the strongest specific metric AND
   compare it to the sector median when relevant. Use the percentiles to
   identify what is exceptional ("ranks in the top 5% of its sector on Value").
2. **What headlines add (if anything).** Name the most relevant recent
   headline in one phrase. Skip this sentence if no headline is genuinely
   relevant to the metric story.
3. **The biggest near-term risk.** Tie it to a weak metric ("ROE of 5% vs
   sector median 18% signals operational pressure") or a real headline risk.

Hard rules:
- Use ONLY the numbers in the input payload. Never invent or estimate a
  number that was not provided.
- Never use the words "buy", "recommend", or "should".
- Be specific. Avoid generic phrases like "solid fundamentals" or "strong
  outlook".
- Describe what the data shows; the reader decides.
- Keep it under 80 words total.
"""

MACRO_SYSTEM_PROMPT = """You are writing today's one-paragraph macro and
geopolitics context for a Berlin-based retail investor who trades US and EU
markets.

You receive a list of today's business and markets headlines. Write ONE
paragraph (3-5 sentences) covering the top themes affecting global, US, and
EU equity markets today.

Hard rules:
- Use ONLY the events in the headlines provided. Do not invent events,
  numbers, or quotes.
- No specific tickers. No buy/sell language. No predictions.
- Be specific: name the central bank, the policy, the region, the sector.
  Avoid vague mood ("markets uncertain", "investors cautious").
- Keep it under 120 words.
"""


SYNTHESIS_SYSTEM_PROMPT = """You are the chief equity strategist for a
European boutique, writing today's read for sophisticated retail investors in
Berlin who trade US and EU markets. Your voice is institutional but plain —
specific, opinionated, never breathless. Think Druckenmiller, not CNBC.

You receive:
- ranked_picks: today's top N picks with ticker, name, sector, region,
  composite score, per-component percentiles, raw metrics, narrative
- composition: aggregate stats (sector counts, region counts, average
  component tilts, composite range)
- macro_context: today's macro paragraph
- universe_meta: total tickers screened and sectors NOT represented in the
  top picks (conspicuous absences are signal)

Write a THREE-paragraph "Strategist's read", ~220 words total:

**Paragraph 1 — What the screen is telling us today.**
Open with the dominant factor or tilt visible in the composition (e.g.,
"Today's screen leans hard into European value — 6 of 10 picks are EU stocks
ranking above the 80th percentile on Value within their sectors."). Cite
concrete composition numbers. Name the dominant sector if there is one. If
the picks are unusually cheap, unusually high-quality, etc., say so.

**Paragraph 2 — The threads connecting these picks.**
Identify 2-3 picks that share a common thesis and explain it in one breath
("Vodafone, Telefónica, and BT all surface on Yield + Value as the European
telecom dividend trade reasserts itself against a backdrop of [macro detail]").
Weave in the macro context where it actually changes how to read a pick. Use
ticker names. Don't force connections that aren't there — if the screen is
heterogeneous, say so.

**Paragraph 3 — What stands out and what to watch.**
Name the outlier — the pick that doesn't fit the dominant theme but still
made the top of the screen. Call out the conspicuous absence (if Tech has
200+ members and zero made the top 10, that's worth flagging). End with the
1-2 macro events from the context that could most credibly flip these
positions in the next two weeks.

Hard rules:
- Use ONLY numbers, tickers, sectors, and events present in the input.
  Never invent metrics, headlines, or events.
- Never use "buy", "recommend", "should", or "target price". Frame
  everything as observations about what the data shows.
- Be specific. "Tech-heavy" is weak; "5 of 10 picks are in Technology
  averaging 87th-percentile Quality" is the bar.
- Have a point of view. If concentration is a risk, say "concentration
  risk". If the macro contradicts the picks, say so.
- No emojis, no headers in your output — just three plain paragraphs
  separated by blank lines.
- Avoid clichés: "interesting times", "navigate volatility", "stay nimble".
"""


def _build_pick_payload(pick: dict, headlines: list[dict]) -> str:
    """Build the JSON string sent to Claude for one pick.

    Reads `raw_metrics` and `scores` (the canonical pipeline names) but also
    falls back to `metrics` / `percentiles` for the standalone smoke-test
    sample at the bottom of this module.
    """
    payload: dict[str, Any] = {
        "ticker": pick.get("ticker"),
        "name": pick.get("name"),
        "sector": pick.get("sector"),
        "currency": pick.get("currency"),
        "last_close": pick.get("last_close"),
        "metrics": pick.get("raw_metrics") or pick.get("metrics", {}),
        "percentiles": pick.get("scores") or pick.get("percentiles", {}),
        "sector_medians": pick.get("sector_medians", {}),
        "headlines": [
            {"title": h.get("title"), "publisher": h.get("publisher")}
            for h in (headlines or [])[:5]
        ],
    }
    return json.dumps(payload, indent=2, default=str)


def narrate_pick(client: Anthropic, pick: dict, headlines: list[dict]) -> str:
    """Return Claude's 2-3 sentence narrative for one pick.

    System prompt is cached so that successive picks within a 5-minute window
    pay ~10% of normal input cost on the persona/format block.
    """
    msg = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": _build_pick_payload(pick, headlines)}],
    )
    return msg.content[0].text.strip()


def narrate_macro(client: Anthropic, headlines: list[dict]) -> str:
    """One paragraph on today's macro / geopolitics context affecting markets."""
    headline_block = "\n".join(
        f"- {h['title']}" + (f" ({h['publisher']})" if h.get("publisher") else "")
        for h in headlines[:15]
    )
    msg = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=[
            {
                "type": "text",
                "text": MACRO_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Today's business and markets headlines:\n\n{headline_block}",
            }
        ],
    )
    return msg.content[0].text.strip()


def narrate_synthesis(
    client: Anthropic,
    picks: list[dict],
    composition: dict,
    macro_blurb: str,
    universe_meta: dict,
) -> str:
    """Strategist-level synthesis across today's picks, composition, and macro.

    Returns a 3-paragraph string (paragraphs separated by blank lines).
    """
    payload = {
        "ranked_picks": [
            {
                "rank": i + 1,
                "ticker": p.get("ticker"),
                "name": p.get("name"),
                "sector": p.get("sector"),
                "region": p.get("region"),
                "composite": p.get("composite"),
                "scores": p.get("scores"),
                "raw_metrics": p.get("raw_metrics"),
                "narrative": p.get("narrative"),
            }
            for i, p in enumerate(picks)
        ],
        "composition": composition,
        "macro_context": macro_blurb,
        "universe_meta": universe_meta,
    }
    msg = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=[
            {
                "type": "text",
                "text": SYNTHESIS_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": json.dumps(payload, indent=2, default=str)}],
    )
    return msg.content[0].text.strip()


if __name__ == "__main__":
    import logging
    from pathlib import Path

    from dotenv import load_dotenv

    from buy_candidates.news import macro_headlines, ticker_headlines

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    client = Anthropic()

    # A sample pick that mirrors what main.py will eventually assemble.
    sample_pick = {
        "ticker": "VOD.L",
        "name": "Vodafone Group",
        "sector": "Communication Services",
        "currency": "GBp",
        "last_close": 112.20,
        "metrics": {
            "trailing_pe": 8.5,
            "price_to_book": 0.7,
            "fcf_yield": 0.12,
            "roe": 0.05,
            "debt_to_equity": 95.0,
            "return_3m": 0.04,
            "dividend_yield": 7.8,
        },
        "percentiles": {
            "value": 95.0,
            "quality": 30.0,
            "momentum": 60.0,
            "yield": 92.0,
        },
        "sector_medians": {
            "trailing_pe": 22.0,
            "price_to_book": 2.5,
            "roe": 0.18,
            "dividend_yield": 2.1,
        },
        "composite": 75.0,
    }

    print("\n== Pick narration (VOD.L) ==")
    pick_headlines = ticker_headlines("VOD.L", limit=5)
    print(narrate_pick(client, sample_pick, pick_headlines))

    print("\n== Macro narration ==")
    macro = macro_headlines(limit=12)
    print(narrate_macro(client, macro))
