"""Send the short email teaser linking to the GH Pages dashboard.

Top 3 picks + first sentence of each narrative + macro one-liner + link.
Uses Gmail SMTP with app password (see .env.example).
"""

from __future__ import annotations


def send_teaser(stock_picks, etf_picks, macro_blurb: str, dashboard_url: str) -> None:
    raise NotImplementedError
