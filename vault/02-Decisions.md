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

## Open questions

- **Web search tool for narration** — proposed but not committed. Would let Opus pull live market context at narration time instead of relying only on RSS digest.
- **Liquidity filter** — should we exclude tickers below €1B market cap to avoid surfacing untradeable picks? Probably yes.
