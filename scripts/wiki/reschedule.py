"""Reschedule a wiki page after review — compute new interval, rewrite frontmatter."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import yaml

from scripts.wiki.frontmatter import parse_frontmatter

MULTIPLIERS = {1: 0, 2: 1.2, 3: 2.5, 4: 4.0}
HARD_MIN = 3


def compute_schedule(
    current_interval: int | float,
    rating: int,
    today: str | None = None,
) -> dict:
    """Compute new review_interval and next_review date.

    Rating scale:
      1 (Again) — reset to 1 day
      2 (Hard)  — interval × 1.2, minimum 3
      3 (Good)  — interval × 2.5
      4 (Easy)  — interval × 4.0
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"rating must be 1-4, got {rating}")

    if today is None:
        today = date.today().isoformat()

    if rating == 1:
        new_interval = 1
    elif rating == 2:
        new_interval = max(round(current_interval * MULTIPLIERS[2]), HARD_MIN)
    else:
        new_interval = round(current_interval * MULTIPLIERS[rating])

    next_review = (date.fromisoformat(today) + timedelta(days=new_interval)).isoformat()
    return {"review_interval": new_interval, "next_review": next_review}


def reschedule_page(
    page_path: Path,
    rating: int,
    today: str | None = None,
) -> dict:
    """Rewrite a wiki page's frontmatter with new schedule. Returns the new schedule."""
    content = page_path.read_text()
    meta, body = parse_frontmatter(content)

    if not meta:
        raise ValueError(f"No frontmatter found in {page_path}")

    current_interval = meta.get("review_interval", 3)
    schedule = compute_schedule(current_interval, rating, today)

    meta["review_interval"] = schedule["review_interval"]
    meta["next_review"] = schedule["next_review"]

    # Rebuild file: frontmatter + body
    fm_text = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    page_path.write_text(f"---\n{fm_text}---\n{body}")

    return schedule
