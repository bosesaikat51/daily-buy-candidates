# Sector-relative scoring

## The problem

Absolute composite scores across all sectors produce trivial, repetitive results:

- **Value** metrics (low P/E, low P/B) → utilities and energy always win, tech always loses
- **Growth/Momentum** → tech always wins, utilities always lose
- **Yield** → REITs and utilities always win, growth tech always loses

A composite combining these absolutely tends to surface the same kind of company every day. Boring, not actionable, and not what an experienced reader needs.

## The fix

Rank each metric **within sector** (percentile 0-100), then combine.

This reframes the question: *"Is this company cheap **for a tech company**?"* instead of *"Is this company cheap **vs. all companies**?"*

## In our pipeline (per `score.py`)

For each metric:

1. Group by sector (from `yfinance.Ticker.info["sector"]`)
2. Within each group, compute percentile rank (0-100)
3. For "lower is better" metrics (P/E, P/B, debt/equity), invert: `100 - percentile`
4. Combine using configured weights:
   - Value 0.35
   - Quality 0.25
   - Momentum 0.25
   - Yield 0.15

## Why these specific weights

Mostly intuition + standard quant practice. Value gets the largest because cheap-looking companies are usually cheap for a reason — letting Value dominate would surface value traps; balancing it with Quality (ROE, low debt) filters those out. The 35/25/25/15 split is a starting point and can be tuned by looking at the past-picks archive.

## ETFs need a different path

ETFs don't have P/E or ROE in the same sense. They'll be scored separately on momentum + AUM + TER + dividend yield. See `score.py::score_etfs`.

## Open question

Should we apply a **minimum liquidity filter** (e.g., market cap > €1B, daily volume > X) before scoring? Avoids surfacing micro-caps that look great on paper but are untradeable in size on TR/Scalable. Probably yes — log it in [[02-Decisions]] when decided.

## References to read

- "Quantitative Equity Portfolio Management" (Chincarini & Kim) — chapter on composite scoring
- AQR papers on factor investing (free PDFs on their site)
- "Your Complete Guide to Factor-Based Investing" (Berkin & Swedroe) — accessible intro
