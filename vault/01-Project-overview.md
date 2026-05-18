# Project overview

## What

A daily-cadence dashboard that ranks stocks and ETFs I can buy on Scalable Capital or Trade Republic, with Claude-written narration per pick.

## Why

Builds on the daily-finance-digest news email (separate repo at `Documents/daily-finance-digest`). The digest tells me what *happened*; this dashboard tells me what *looks interesting today* based on fundamentals + recent news + macro context.

## Stack

- Python 3.12, managed by `uv`
- yfinance for fundamentals + prices (free, no API key)
- Anthropic SDK (Claude Opus 4.7) for narration
- Jinja2 templates → static HTML in `docs/`
- GitHub Actions runs the whole pipeline at 22:30 Berlin (post-US-close)
- GitHub Pages serves the rendered dashboard
- Gmail SMTP for the daily email teaser

## How it runs end-to-end

1. Cron triggers `daily.yml` at 21:30 UTC
2. Workflow checks out repo, runs `uv sync`, executes `python -m buy_candidates.main`
3. Pipeline: universe → data → score → news → narrate → archive → render → email
4. Workflow commits `docs/` + new `archive/YYYY-MM-DD.json` back to the repo
5. GitHub Pages serves the updated `docs/index.html`
6. I get an email teaser with the top 3 + link to the full dashboard

## Tutorial #4 in my learning journey

1. daily-finance-digest (done)
2. weekly-food-picks (done)
3. Telegram finance bot (not started)
4. **daily-buy-candidates** ← this one, scaffolded 2026-05-18

## What's intentionally not in scope (yet)

- Investment projection calculator (deferred to [[08-TODO|Phase 4]])
- Real-time / intraday updates (evening cadence is enough)
- Backtesting the screener (past-picks archive is a poor-man's substitute)
- Order placement integration (deliberately *not* a robo-advisor — informational only)
