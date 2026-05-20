"""Daily run snapshot to archive/YYYY-MM-DD.json.

Persists the picks, narratives, synthesis, composition stats, and macro
context so the past-picks page can reconstruct a poor-man's track record
later.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

ARCHIVE_DIR = Path(__file__).resolve().parents[2] / "archive"

log = logging.getLogger(__name__)


def _scrub_for_json(obj: Any) -> Any:
    """Drop any non-JSON-serializable artifacts (pandas/numpy types, etc.)."""
    if isinstance(obj, dict):
        return {k: _scrub_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_for_json(v) for v in obj]
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:  # noqa: BLE001
            return str(obj)
    return obj


def save_daily(
    as_of: date,
    stock_picks: list[dict],
    etf_picks: list[dict],
    macro_blurb: str,
    synthesis: str,
    composition: dict,
    universe_meta: dict,
) -> Path:
    """Write today's snapshot to archive/YYYY-MM-DD.json. Returns the path."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE_DIR / f"{as_of.isoformat()}.json"
    snapshot = {
        "as_of": as_of.isoformat(),
        "universe_meta": universe_meta,
        "composition": composition,
        "macro_blurb": macro_blurb,
        "synthesis": synthesis,
        "stock_picks": stock_picks,
        "etf_picks": etf_picks,
    }
    path.write_text(
        json.dumps(_scrub_for_json(snapshot), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("archived run to %s", path)
    return path
