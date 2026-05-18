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

### Confirmed in Phase 1 smoke test (2026-05-18)

- **UK stocks price in GBp (pence), not GBP.** `VOD.L last_close=112.20` is 1.122 GBP. Need to either divide by 100 in display for `.L` tickers, or label the unit clearly. Other currencies are in their major unit.
- **`dividend_yield` is in percent** in current yfinance (1.3.0): `AAPL` returned `0.36` for ~0.36%, `NESN.SW` returned `3.97` for ~3.97%. **`return_3m` is a fraction** (`0.143` = 14.3%). Don't mix units — percentile-rank each column independently in score.py.
- **yfinance `sector` ≠ Wikipedia sector.** yfinance uses Morningstar names (`Technology`, `Consumer Defensive`, `Communication Services`); Wikipedia uses GICS for S&P 500 and ICB for STOXX 600. **Sector-relative scoring must group by the yfinance `sector` column** — Wikipedia's is only a fallback for entries where yfinance returns None.
- **ETFs return mostly None** for fundamentals (`trailing_pe`, `roe`, `debt_to_equity` are all NaN for VWCE.DE) — keep the row anyway, just gives no ranking on those columns. ETFs end up scored on momentum + yield only.
- **`yf.download` with multiple tickers returns a MultiIndex column frame**, but a flat one for a single ticker. data.py handles both.

## Caching plan

Per-ticker parquet file at `cache/{ticker}_{YYYYMMDD}.parquet`. Same-day re-runs skip the network entirely. Older files pruned by date (keep last 7 days).

## Free alternatives if yfinance becomes unworkable

- **Financial Modeling Prep** — free tier with daily limits, more reliable
- **Alpha Vantage** — free API key, 25 requests/day on free tier (too limited for this)
- **SEC EDGAR** — gold standard for US fundamentals, but US-only and the API is unergonomic
- **Stooq** — free EU data, CSV exports

For now yfinance is fine; track failures and revisit if quality drops.
