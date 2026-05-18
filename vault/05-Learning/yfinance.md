# yfinance

## What it is

Unofficial Python wrapper around Yahoo Finance's web API. Free, no API key, but unreliable in subtle ways.

## What I'll use from it

```python
import yfinance as yf

t = yf.Ticker("NVDA")
t.info          # fundamentals dict (P/E, ROE, sector, market cap, etc.)
t.history(period="1y")   # OHLCV DataFrame
t.news          # recent news items
```

## Known gotchas

- **Rate-limited** when fetching many tickers fast. For ~700 tickers, batch in groups of ~30 with small sleeps + retry-with-backoff on 429s.
- **STOXX 600 fundamentals are spottier** than S&P 500. Some EU tickers return empty `info` dicts or missing keys. Plan: skip silently rather than crash; log which were dropped.
- **Currency varies** — EU stocks in EUR/GBP/CHF, US in USD. Either show native + EUR-converted, or normalize to EUR before display. Decision pending.
- **Field names can change** between yfinance versions. Pin a known-good version in `pyproject.toml`.
- **Yahoo can serve stale data on weekends** — Friday close persists. Fine for a Sunday-evening rerun.

## Caching plan

Per-ticker parquet file at `cache/{ticker}_{YYYYMMDD}.parquet`. Same-day re-runs skip the network entirely. Older files pruned by date (keep last 7 days).

## Free alternatives if yfinance becomes unworkable

- **Financial Modeling Prep** — free tier with daily limits, more reliable
- **Alpha Vantage** — free API key, 25 requests/day on free tier (too limited for this)
- **SEC EDGAR** — gold standard for US fundamentals, but US-only and the API is unergonomic
- **Stooq** — free EU data, CSV exports

For now yfinance is fine; track failures and revisit if quality drops.
