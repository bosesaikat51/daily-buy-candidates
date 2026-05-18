# Architecture

## Data flow

```
data/universe.yaml  +  Wikipedia (S&P 500, STOXX 600)
              |
              v
        universe.py  --- list of tickers
              |
              v
          data.py  --- batched yfinance fetch + parquet cache
              |
              v       (DataFrame: ticker, sector, P/E, ROE, etc.)
              |
              +-------- score.py  --- sector-relative composite, top N
              |              |
              |              v
              |          news.py (RSS + per-ticker headlines)
              |              |
              |              v
              |        narrate.py  --- Claude Opus 4.7
              |              |
              |              v
              +------> archive.py  --- archive/YYYY-MM-DD.json
                             |
                             v
                        render.py  --- docs/index.html (+ tickers/*.html later)
                             |
                             v
                    email_digest.py  --- Gmail SMTP teaser
```

## Module responsibilities

| Module | Owns | Inputs | Outputs |
|--------|------|--------|---------|
| `universe.py` | The ticker list | YAML + Wikipedia | `list[dict]` of {ticker, name, asset_class, region} |
| `data.py` | Fundamentals + prices | tickers | DataFrame keyed by ticker |
| `score.py` | Sector-relative ranking | fundamentals DataFrame | sorted picks with score breakdown |
| `news.py` | Recent headlines | tickers + RSS URLs | per-ticker headlines + macro pool |
| `narrate.py` | Claude narration | picks + headlines | strings (short per-pick + long-form per ticker + macro paragraph) |
| `archive.py` | Daily JSON persistence | picks + macro | `archive/YYYY-MM-DD.json` |
| `render.py` | HTML generation | picks + narratives + macro | `docs/index.html` (+ later `docs/tickers/*.html`, `docs/past_picks.html`) |
| `email_digest.py` | Email teaser | top 3 picks + macro + URL | sent email via Gmail SMTP |
| `main.py` | Orchestration | nothing | runs the whole pipeline |

## Caches

- `cache/{ticker}_{YYYYMMDD}.parquet` — per-ticker yfinance pull (avoids same-day re-fetch)
- `cache/narratives/{TICKER}.json` — long-form Claude narrative + timestamp (Phase 3, refreshes weekly)

Both are gitignored.

## Secrets (GitHub Actions)

- `ANTHROPIC_API_KEY`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `EMAIL_TO`
- `DASHBOARD_URL`

See `.env.example` for the local equivalents.

## Why the `src/` layout

Putting code in `src/buy_candidates/` (not `buy_candidates/` at repo root) forces `uv sync` to actually install the package before imports work. Catches packaging mistakes early instead of only failing in CI. See [[05-Learning/uv-and-pyproject]].
