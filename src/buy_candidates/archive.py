"""Persist daily picks to archive/YYYY-MM-DD.json for the track-record page."""

from __future__ import annotations

from pathlib import Path

ARCHIVE_DIR = Path(__file__).resolve().parents[2] / "archive"


def save_daily(stock_picks, etf_picks, macro_blurb: str, as_of) -> Path:
    """Write archive/YYYY-MM-DD.json and return the path."""
    raise NotImplementedError
