"""Parse and dump YAML frontmatter, slugify titles."""

from __future__ import annotations

import datetime
import re

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split file content into parsed YAML metadata and body.

    Returns ({}, content) if no valid frontmatter found.
    Post-processes datetime.date values to ISO strings and
    flashcard_ids to list of strings.
    """
    if not content.startswith("---\n"):
        return {}, content

    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1]
    body = parts[2]

    meta = yaml.safe_load(fm_text)
    if not isinstance(meta, dict):
        return {}, content

    # Post-process: dates to ISO strings
    for key, val in meta.items():
        if isinstance(val, (datetime.date, datetime.datetime)):
            meta[key] = val.isoformat()

    # Post-process: flashcard_ids to list of strings
    if "flashcard_ids" in meta:
        ids = meta["flashcard_ids"]
        if isinstance(ids, list):
            meta["flashcard_ids"] = [str(x) for x in ids]
        else:
            meta["flashcard_ids"] = []

    return meta, body


def slugify(title: str) -> str:
    """Slugify a title: lowercase, non-alphanumeric to hyphens, collapse, strip."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s
