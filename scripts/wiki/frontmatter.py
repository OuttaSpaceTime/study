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

    for key, val in meta.items():
        if isinstance(val, datetime.date):
            meta[key] = val.isoformat()

    for key in ("flashcard_ids", "probe_sections", "last_probed"):
        if key in meta:
            val = meta[key]
            meta[key] = [str(x) for x in val] if isinstance(val, list) else []

    return meta, body


def dump_page(meta: dict, body: str) -> str:
    """Render a wiki page: YAML frontmatter + body."""
    fm = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm}---\n{body}"


_H2_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def extract_h2s(body: str) -> list[str]:
    """Return H2 heading texts from a page body, in document order."""
    return [m.strip() for m in _H2_RE.findall(body)]


def normalize_heading(s: str) -> str:
    """Normalize for H2-heading matching: lowercase, strip trailing .?!: and whitespace."""
    return s.strip().rstrip(".?!:").lower()


def norm_set(sections: list[str]) -> set[str]:
    return {normalize_heading(s) for s in sections}


def slugify(title: str) -> str:
    """Slugify a title: lowercase, non-alphanumeric to hyphens, collapse, strip."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s
