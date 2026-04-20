"""Read/write .wiki-index.json and update entries from wiki pages."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

from scripts.wiki.frontmatter import extract_h2s, parse_frontmatter


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


def iter_wiki_pages(wiki_dir: Path) -> list[Path]:
    """Return all wiki markdown pages (sorted), skipping Obsidian metadata."""
    return sorted(
        p for p in wiki_dir.rglob("*.md") if ".obsidian" not in p.parts
    )


def update_entry(index: dict, wiki_dir: Path, page_path: Path) -> dict:
    """Parse a wiki page and update the index entry. Returns the updated index."""
    content = page_path.read_text()
    meta, body = parse_frontmatter(content)

    sections = extract_h2s(body)
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
        "category": meta.get("category"),
        "sections": sections,
        "flashcard_ids": meta.get("flashcard_ids", []),
        "created": meta.get("created", today),
        "updated": today,
        "next_review": meta.get("next_review", ""),
        "review_interval": meta.get("review_interval"),
        "probe_sections": meta.get("probe_sections", []),
        "last_probed": meta.get("last_probed", []),
    }

    return index
