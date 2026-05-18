"""Claude narration of quant-selected picks.

Uses claude-opus-4-7 for quality. Prompt caching applied to SYSTEM_PROMPT so
the persona + format spec is cached across all picks within a run (and across
runs within the 5-minute TTL window — irrelevant here since it's a single run,
but good hygiene).

Claude never invents a buy. It only narrates what the screener surfaced.
"""

from __future__ import annotations

from anthropic import Anthropic

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """You are a sober equity analyst writing for an experienced
retail investor in Berlin who trades US and EU markets. For each pick you
receive, write 2-3 tight sentences covering, in this order:

1. The strongest reason the screener flagged it (cite the specific metric).
2. The most relevant recent headline if any (one phrase, no link).
3. The biggest near-term risk to watch.

Be specific. Never invent numbers. Never use the words "buy", "recommend",
or "should". Describe what the data shows; the reader decides."""


def narrate_pick(client: Anthropic, pick: dict, headlines: list[dict]) -> str:
    """Return Claude's 2-3 sentence narrative for one pick. Uses cache_control."""
    raise NotImplementedError


def narrate_macro(client: Anthropic, headlines: list[dict]) -> str:
    """One paragraph on today's macro / geopolitics context affecting markets."""
    raise NotImplementedError
