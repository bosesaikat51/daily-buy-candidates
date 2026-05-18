"""Render dashboard.html.j2 -> docs/index.html, plus past_picks page."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = REPO_ROOT / "templates"
OUTPUT_DIR = REPO_ROOT / "docs"


def render_dashboard(stock_picks, etf_picks, macro_blurb: str, as_of) -> None:
    """Render docs/index.html from templates/dashboard.html.j2."""
    raise NotImplementedError


def render_past_picks() -> None:
    """Render docs/past_picks.html by reading archive/*.json."""
    raise NotImplementedError
