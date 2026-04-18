"""Read/write .wiki-index.json and update entries from wiki pages."""

from __future__ import annotations

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter


def load_index(index_path: Path) -> dict:
    """Load the wiki index, returning {} if the file doesn't exist or is corrupt."""
    if not index_path.exists():
        return {}
    text = index_path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        backup = index_path.with_suffix(".json.bak")
        shutil.copy2(index_path, backup)
        print(f"Warning: corrupt index, backed up to {backup}: {e}", file=sys.stderr)
        return {}


def save_index(index_path: Path, index: dict) -> None:
    """Write the wiki index as indented JSON with trailing newline."""
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_wiki_key(wiki_dir: Path, page_path: Path) -> str:
    """Compute the wiki key: relative path without .md extension."""
    rel = page_path.relative_to(wiki_dir)
    return str(rel.with_suffix(""))


def update_entry(index: dict, wiki_dir: Path, page_path: Path) -> dict:
    """Parse a wiki page and update the index entry. Returns the updated index."""
    content = page_path.read_text()
    meta, body = parse_frontmatter(content)

    sections = re.findall(r"^## (.+)$", body, re.MULTILINE)
    wiki_key = get_wiki_key(wiki_dir, page_path)
    rel_path = str(page_path.relative_to(wiki_dir))
    today = date.today().isoformat()

    aliases = meta.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = [aliases]

    tags = meta.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags]

    index[wiki_key] = {
        "file": rel_path,
        "title": meta.get("title", ""),
        "aliases": aliases,
        "tags": tags,
        "sections": sections,
        "flashcard_ids": meta.get("flashcard_ids", []),
        "created": meta.get("created", today),
        "updated": today,
        "next_review": meta.get("next_review", ""),
        "review_interval": meta.get("review_interval"),
    }

    return index
