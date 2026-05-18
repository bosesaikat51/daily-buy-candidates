# TODO

Phased build plan. Check items off as they ship.

## Side / unblockers

- [x] Decide hosting → **everything public** (free GH Pages from public repo)
- [ ] `git init` locally, create public GH repo `daily-buy-candidates`, push
- [ ] Enable GitHub Pages from `/docs` on the default branch
- [ ] Add the 5 GH Actions secrets (`ANTHROPIC_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO`, `DASHBOARD_URL`)
- [ ] First end-to-end manual run via `workflow_dispatch`

## Phase 1 — wire core pipeline

- [ ] `universe.py` — Wikipedia scrape + YAML loader
- [ ] `data.py` — batched yfinance fetch + parquet cache
- [ ] `score.py` — sector-relative composite + ETF scoring
- [ ] `news.py` — RSS macro pool + per-ticker headlines
- [ ] `narrate.py` — Claude short narration with prompt caching
- [ ] `archive.py` — daily JSON snapshot
- [ ] `render.py` — render `docs/index.html` from real picks
- [ ] `email_digest.py` — Gmail SMTP teaser
- [ ] First green daily run via GitHub Actions

## Phase 2 — sparklines

- [ ] Server-side inline SVG sparkline generator
- [ ] Slot sparkline into pick cards (under score row)
- [ ] Wire price-history fetch into `data.py` (probably already there)

## Phase 3 — per-ticker detail pages

- [ ] `docs/tickers/{TICKER}.html` route + template
- [ ] Full metrics (open, close, 52w hi/lo, market cap, beta, sector P/E vs ticker P/E, debt ratios)
- [ ] 1Y / 5Y / MAX price chart (server-rendered SVG)
- [ ] Quarterly revenue / EPS / FCF mini-charts
- [ ] Long-form Claude (bull case + bear case + macro frame) at `cache/narratives/{TICKER}.json`
- [ ] Refresh logic: only on re-entry to top 10 OR >7 days old
- [ ] Investigate Claude web search tool for richer macro context
- [ ] Past-picks page reads `archive/*.json` and shows "then vs now"

## Phase 4 — projection calculator (deferred)

- [ ] Standalone `/projection` page
- [ ] Sliders for bulk + monthly + years + assumed annual return
- [ ] Conservative defaults (6% real return — not ticker CAGR)
- [ ] Strong disclaimer banner

## Nice-to-haves (no commitment)

- [ ] Liquidity filter (min market cap €1B) before scoring
- [ ] Sector heatmap on the dashboard
- [ ] Weekly digest email (Sunday summary)
- [ ] Telegram bot integration (reuse logic from Tutorial #3 once that's built)
