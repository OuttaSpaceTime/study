"""Reschedule a wiki page after review — compute new interval, rewrite frontmatter."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from scripts.wiki.frontmatter import (
    dump_page,
    norm_set,
    normalize_heading,
    parse_frontmatter,
)

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


def rotate_last_probed(
    probe_sections: list[str],
    last_probed: list[str],
    probed: list[str],
) -> list[str]:
    """Return the new last_probed queue after probing `probed` sections.

    Queue invariant at rest: {normalize(s) for s in last_probed} == {normalize(s) for s in probe_sections}.
    If drifted (empty, missing, or extras), reinitialize from probe_sections order.
    Then move probed entries to the tail so the oldest-unprobed is next.
    """
    ps_norm_to_canon = {normalize_heading(s): s for s in probe_sections}
    if norm_set(last_probed) != set(ps_norm_to_canon):
        queue = list(probe_sections)
    else:
        queue = [ps_norm_to_canon[normalize_heading(s)] for s in last_probed]

    probed_norms = norm_set(probed)
    head = [s for s in queue if normalize_heading(s) not in probed_norms]
    tail = [s for s in queue if normalize_heading(s) in probed_norms]
    return head + tail


def reschedule_page(
    page_path: Path,
    rating: int,
    today: str | None = None,
    probed: list[str] | None = None,
) -> dict:
    """Rewrite a wiki page's frontmatter with new schedule. Returns the new schedule.

    If `probed` is given, rotates `last_probed` to move those sections to the end
    of the queue (oldest-first ordering).
    """
    content = page_path.read_text()
    meta, body = parse_frontmatter(content)

    if not meta:
        raise ValueError(f"No frontmatter found in {page_path}")

    current_interval = meta.get("review_interval", 3)
    schedule = compute_schedule(current_interval, rating, today)

    meta["review_interval"] = schedule["review_interval"]
    meta["next_review"] = schedule["next_review"]

    if probed is not None:
        meta["last_probed"] = rotate_last_probed(
            meta.get("probe_sections") or [],
            meta.get("last_probed") or [],
            probed,
        )

    page_path.write_text(dump_page(meta, body))
    return schedule
