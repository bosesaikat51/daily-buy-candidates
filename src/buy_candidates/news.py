"""News fetching: per-ticker (yfinance) + macro (BBC / CNBC / FT / Handelsblatt RSS).

Both functions are defensive — yfinance's `.news` schema has shifted between
versions, and any individual feed can 404 or rate-limit without warning. We log
and continue rather than fail the daily run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import struct_time
from typing import Any

import feedparser
import yfinance as yf

MACRO_FEEDS = [
    "http://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.ft.com/markets?format=rss",
    "https://www.handelsblatt.com/contentexport/feed/schlagzeilen",
]

USER_AGENT = (
    "daily-buy-candidates/0.1 "
    "(+https://github.com/bosesaikat51/daily-buy-candidates)"
)

log = logging.getLogger(__name__)


def _from_struct_time(st: struct_time | None) -> datetime | None:
    if st is None:
        return None
    return datetime(*st[:6], tzinfo=timezone.utc)


def _from_unix(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (ValueError, OSError):
        return None


def _yf_item_to_dict(item: dict[str, Any]) -> dict | None:
    """Normalize one yfinance .news entry. Handles both old (flat) and new
    (nested ``content`` dict) schemas."""
    content = item.get("content")
    if isinstance(content, dict):
        title = content.get("title")
        url = (
            (content.get("canonicalUrl") or {}).get("url")
            or (content.get("clickThroughUrl") or {}).get("url")
        )
        publisher = (content.get("provider") or {}).get("displayName")
        pub_str = content.get("pubDate")
        published: datetime | None = None
        if pub_str:
            try:
                published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except ValueError:
                published = None
    else:
        title = item.get("title")
        url = item.get("link")
        publisher = item.get("publisher")
        published = _from_unix(item.get("providerPublishTime"))

    if not title or not url:
        return None
    return {
        "title": title.strip(),
        "url": url,
        "published": published.isoformat() if published else None,
        "publisher": publisher,
    }


def ticker_headlines(ticker: str, limit: int = 5) -> list[dict]:
    """Recent headlines for one ticker — [{title, url, published, publisher}, ...].

    Sorted newest first. Returns [] if yfinance raises or returns nothing."""
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception as e:  # noqa: BLE001 — yfinance raises a wide net
        log.warning("yfinance .news failed for %s: %s", ticker, e)
        return []

    items: list[dict] = []
    for r in raw:
        norm = _yf_item_to_dict(r)
        if norm is not None:
            items.append(norm)

    items.sort(key=lambda x: x["published"] or "", reverse=True)
    return items[:limit]


def _rss_entry_to_dict(entry: Any, feed_url: str) -> dict | None:
    title = getattr(entry, "title", None)
    url = getattr(entry, "link", None)
    if not title or not url:
        return None

    published = _from_struct_time(
        getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    )
    src = getattr(entry, "source", None)
    publisher = src.get("title") if src else None

    return {
        "title": title.strip(),
        "url": url,
        "published": published.isoformat() if published else None,
        "publisher": publisher,
        "source_feed": feed_url,
    }


def _fetch_feed(url: str) -> list[dict]:
    parsed = feedparser.parse(url, agent=USER_AGENT)
    if not parsed.entries:
        reason = getattr(parsed, "bozo_exception", None) or "no entries returned"
        log.warning("feed %s: %s", url, reason)
        return []
    out: list[dict] = []
    for e in parsed.entries:
        norm = _rss_entry_to_dict(e, url)
        if norm is not None:
            out.append(norm)
    return out


def macro_headlines(limit: int = 10) -> list[dict]:
    """Today's top macro / geopolitics headlines across MACRO_FEEDS.

    Deduped by case-folded title (same story across multiple feeds), newest
    first. Returns up to `limit` items."""
    all_items: list[dict] = []
    for url in MACRO_FEEDS:
        all_items.extend(_fetch_feed(url))

    seen: set[str] = set()
    deduped: list[dict] = []
    for item in all_items:
        key = item["title"].casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda x: x["published"] or "", reverse=True)
    return deduped[:limit]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print("\n== Macro headlines ==")
    macro = macro_headlines(limit=8)
    for h in macro:
        print(f"  [{(h['published'] or '')[:10]}] {h['title'][:90]}")
        print(f"    {h['publisher'] or h['source_feed']}")
    print(f"  ({len(macro)} returned)")

    print("\n== Ticker headlines (AAPL) ==")
    tic = ticker_headlines("AAPL", limit=5)
    for h in tic:
        print(f"  [{(h['published'] or '')[:10]}] {h['title'][:90]}")
        print(f"    {h['publisher']}")
    print(f"  ({len(tic)} returned)")
