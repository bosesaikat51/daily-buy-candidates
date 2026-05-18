# Anthropic API (Claude)

## Model for this project

`claude-opus-4-7` — Anthropic's most capable model (as of 2026-05). Used for both:

- **Short narration** per pick (2-3 sentences, daily, ~10 picks)
- **Long-form narration** per ticker (bull/bear/macro paragraphs, cached 7 days)

## Cost rough estimate

- ~10 picks/day × ~150 output tokens = ~1.5K output tokens/day for short
- Long-form: 10 tickers × ~600 tokens, but cached weekly = effectively ~1.5 long-forms/day on average
- Net: maybe €0.30-€1.00/day worst case, €0.10-€0.30/day typical
- ~€100/year worst case — trivial relative to dashboard value

## Prompt caching

Anthropic supports `cache_control` markers on prompt blocks. Cached blocks cost ~10% of normal input price on cache hits. TTL is 5 minutes.

In this project: mark the `SYSTEM_PROMPT` in `narrate.py` as cacheable so it's reused across all 10 picks in a single run. Saving is small in absolute terms but free to add.

```python
client.messages.create(
    model="claude-opus-4-7",
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ],
    messages=[...],
)
```

## Web search tool (proposed, not committed)

Anthropic's API supports a `web_search_*` tool that lets Claude fetch live web content during a response. Would let long-form narration pull current market context ("Dutch export rules this week") instead of only what our RSS digest happened to capture. Worth wiring into the long-form path in [[08-TODO|Phase 3]].

Cost: small per-search fee on top of normal tokens. Trivial for ~10 picks/day.

## Anti-hallucination guardrails in our prompt

The `SYSTEM_PROMPT` in `narrate.py` enforces:

- "Never invent numbers"
- "Never use the words buy/recommend/should"
- "Describe what the data shows; the reader decides"

Plus we **pass structured input** (fundamentals dict + headlines list), not free-form narrative. The smaller the gap between input and output, the harder it is for Claude to drift.
