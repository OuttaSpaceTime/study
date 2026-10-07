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

    # The C loader where PyYAML has it: YAML is most of an index build.
    meta = yaml.load(fm_text, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    if not isinstance(meta, dict):
        return {}, content

    for key, val in meta.items():
        if isinstance(val, datetime.date):
            meta[key] = val.isoformat()

    if "flashcard_ids" in meta:
        val = meta["flashcard_ids"]
        meta["flashcard_ids"] = [str(x) for x in val] if isinstance(val, list) else []

    return meta, body


def dump_page(meta: dict, body: str) -> str:
    """Render a wiki page: YAML frontmatter + body."""
    fm = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm}---\n{body}"


_H2_RE = re.compile(r"^##[ \t]+(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def extract_h2s(body: str) -> list[str]:
    """Return H2 heading texts from a page body, in document order.

    A `## ` line inside a fenced block (a shell comment, say) is not a heading.
    """
    out, in_fence = [], False
    for line in body.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and (m := _H2_RE.match(line)):
            out.append(m.group(1))
    return out


def slugify(title: str) -> str:
    """Slugify a title: lowercase, non-alphanumeric to hyphens, collapse, strip."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    return s
