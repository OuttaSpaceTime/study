"""A wiki page read once, shared by every lint check."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter


@dataclass
class ParsedPage:
    path: Path
    rel: str
    raw: str
    meta: dict
    body: str


def parse_pages(wiki_dir: Path, md_files: list[Path]) -> list[ParsedPage]:
    """Read and parse each page once; shared across all lint checks."""
    pages = []
    for f in md_files:
        raw = f.read_text()
        meta, body = parse_frontmatter(raw)
        pages.append(ParsedPage(f, str(f.relative_to(wiki_dir)), raw, meta, body))
    return pages
