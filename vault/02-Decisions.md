# Decisions log

Running record of choices made for this project, with reasoning. Newest at top.

---

## 2026-05-18 · Initial scope and scaffolding

### Universe: S&P 500 + STOXX 600 + curated ETFs (~700+ tickers)
Sourced from Wikipedia constituent tables + a maintained YAML in `data/universe.yaml`. Reason: broad enough to surface non-obvious picks, narrow enough to scan in reasonable time. Tickers with chronically bad yfinance data go in `excluded_tickers`.

### Scoring: sector-relative composite
- Value (P/E, P/B, FCF yield) — weight 0.35
- Quality (ROE, debt/equity) — weight 0.25
- Momentum (3m return) — weight 0.25
- Yield (dividend yield) — weight 0.15

Each metric is percentile-ranked **within sector**, not globally. Avoids tech always losing on P/E and utilities always winning on yield. See [[05-Learning/Sector-relative-scoring]].

### LLM role: narrate, never invent
Claude (Opus 4.7) gets the quant-selected picks + fundamentals + recent headlines, and writes 2-3 sentences. It does *not* generate picks. Reason: quant prefilter is reproducible; Claude adds context the numbers can't show. See [[05-Learning/Anthropic-API]].

### Schedule: 22:30 Berlin (cron `30 21 * * *` UTC)
Always post-US-close (US closes 22:00 Berlin). Accept the ~1h winter/summer DST drift since GH Actions cron can't do timezones.

### Output: GH Pages dashboard + short email teaser
Page = full picks. Email = top 3 + link. Both share the same disclaimer.

### Archive: yes
Daily `archive/YYYY-MM-DD.json` snapshot. Past-picks page reads these for a rough track record (not a backtest).

### Phased build
1. Wire core pipeline
2. Sparklines on cards (inline SVG)
3. Per-ticker detail pages with long-form Claude (bull/bear/macro, cached 7 days)
4. Investment projection calculator (deferred)

### Long-form Claude caching
Per-ticker long-form narration cached at `cache/narratives/{TICKER}.json`. Refresh only on (a) re-entry to top 10 after dropping out, or (b) >7 days old. Cuts Opus cost ~10×.

### Disclaimer is non-negotiable
"Informational, not financial advice" — prominent on dashboard footer, every detail page, and every email.

---

### Hosting: everything public (free)
Repo public on GitHub, Pages public, no cost. Source code reveals nothing sensitive (generic Python, public ticker lists) and picks are public via the dashboard regardless. GH Pro ($4/mo) is a future-promote option if I ever put personal info in commits.

---

## 2026-05-19 (session 4) · Synthesis-tier narration + orchestration

### Three-tier narration: pick / macro / synthesis
The dashboard has three distinct Claude calls now: per-pick (2-3 sentences with sector-median comparatives), macro (1 paragraph from RSS headlines), and **synthesis** (3 paragraphs from strategist persona, reading the entire pick list + composition + macro). The synthesis is what makes the dashboard feel curated rather than mechanical — it identifies cross-pick threads, concentration risk, conspicuous absences, and catalysts. Worth the additional API cost (~$0.015 per run).

### Composition stats computed per run, fed to synthesis
`main.py::_composition_stats` summarizes sector breakdown, region breakdown, average component scores, composite range; `_missing_sectors` flags any sector with ≥10 universe members and zero top-pick representation. Both go into the synthesis payload. Reason: aggregates produce qualitatively better strategist output than the same picks without context.

### ETF narration is mechanical for now
`score_etfs` returns only momentum + yield (no fundamentals to comment on), so the per-ETF narrative is auto-generated from those two numbers instead of a Claude call. Saves cost; revisit if ETFs need richer prose.

### --limit N flag for local iteration
`main.py` accepts `--limit N` to slice the universe. Default (no arg) runs the full ~990 tickers (cron behavior). Local development uses `--limit 100` for 3-5 minute round trips. The fundamentals cache means re-runs on the same day re-execute only the LLM calls.

### Hero headline auto-derived from composition
If a single sector holds ≥half the picks (or ≥3), the H1 reads "{Sector} leads today's screen". Otherwise generic. Cheap signal of conviction tilt visible without reading the synthesis.

---

## 2026-05-19 (session 2) · News sources

### MACRO_FEEDS replaced: Reuters → BBC + CNBC
Original Reuters RSS URL (`feeds.reuters.com/reuters/businessNews`) is dead — Reuters shut down their RSS service years ago and the DNS doesn't resolve. Replaced with BBC Business + CNBC top news, keeping FT and Handelsblatt. Reason: BBC covers world/geopolitics, CNBC covers US markets — together they replace what Reuters used to give us, with the FT (global markets) + Handelsblatt (DE) anchors unchanged.

### Defensive yfinance .news parsing
yfinance returns two different schemas for `.news` depending on version — old flat `{title, link, providerPublishTime, publisher}` and new nested `{content: {title, canonicalUrl, pubDate, provider}}`. We handle both via `isinstance(item.get("content"), dict)` branching. Reason: yfinance upgrades silently break this otherwise.

### Cross-feed dedupe only (case-folded title)
Same wire story syndicated to multiple feeds shows once. Within-feed dedupe is not needed (assume the feed doesn't repeat itself).

---

## 2026-05-19 · Scoring implementation

### Sanitize before rank
Set `trailing_pe <= 0`, `price_to_book <= 0`, `debt_to_equity < 0` to NaN before percentile ranking. Otherwise a loss-maker (negative P/E) would rank as the "cheapest" stock when "lower is better" — wrong, since negative P/E means no earnings.

### Minimum data threshold
Drop rows with fewer than 4 of the 7 core metrics present (`trailing_pe`, `price_to_book`, `fcf_yield`, `roe`, `debt_to_equity`, `return_3m`, `dividend_yield`). A row with only 1-2 metrics produces an unreliable composite.

### Composite renormalization
When a row is missing a whole component (e.g. an industrial with no FCF yield → Value still computes from P/E + P/B), the composite uses a per-row renormalized denominator over the components that *are* present. Reason: penalizing rows for missing data they fundamentally can't have (vs. having and being bad) would conflate "data gap" with "weak fundamental".

### ETFs ranked globally on momentum + yield
ETFs have null sector → can't group. Ranked across the whole ETF set (small list anyway, ~5 today). No P/E or ROE makes sense for an index fund. Accumulating ETFs end up scored on momentum only because yfinance gives them `dividendYield=None`.

### Singleton sectors not handled
With ~990 real tickers every yfinance sector has dozens of members, so singletons aren't a real concern. If they ever show up in a live run, add a `min_sector_size` filter.

---

## Open questions

- **Web search tool for narration** — proposed but not committed. Would let Opus pull live market context at narration time instead of relying only on RSS digest.
- **Liquidity filter** — should we exclude tickers below €1B market cap to avoid surfacing untradeable picks? Probably yes.
- **ETF fallback metrics** — should ETFs without `dividendYield` be filtered, or kept and ranked on momentum alone (current behavior)? Revisit after first live run.
