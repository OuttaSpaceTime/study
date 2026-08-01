"""Read/write .wiki-index.json and update entries from wiki pages."""

from __future__ import annotations

import argparse
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


def reindex_all(wiki_dir: Path) -> dict:
    """Rebuild every index entry from the pages on disk.

    A reindex derives rather than writes: it drops fields the current schema no
    longer produces and prunes entries whose pages are gone, while carrying each
    page's existing ``updated`` stamp over. Rebuilding after a schema change must
    not mark the whole wiki as edited today.
    """
    previous = load_index(wiki_dir / ".wiki-index.json")
    rebuilt: dict = {}
    for page_path in iter_wiki_pages(wiki_dir):
        wiki_key = get_wiki_key(wiki_dir, page_path)
        entry = derive_entry(wiki_dir, page_path)
        entry["updated"] = previous.get(wiki_key, {}).get("updated", entry["updated"])
        rebuilt[wiki_key] = entry
    return rebuilt


def derive_entry(wiki_dir: Path, page_path: Path) -> dict:
    """Build an index entry from a page's content alone.

    ``updated`` defaults to today so a page with no prior entry gets a stamp;
    callers that know no edit happened overwrite it with the value they hold.
    """
    meta, body = parse_frontmatter(page_path.read_text())
    today = date.today().isoformat()

    aliases = meta.get("aliases", [])
    if not isinstance(aliases, list):
        aliases = [aliases]

    tags = meta.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags]

    return {
        "file": str(page_path.relative_to(wiki_dir)),
        "title": meta.get("title", ""),
        "aliases": aliases,
        "tags": tags,
        "sections": extract_h2s(body),
        "flashcard_ids": meta.get("flashcard_ids", []),
        "created": meta.get("created", today),
        "updated": today,
    }


def update_entry(index: dict, wiki_dir: Path, page_path: Path) -> dict:
    """Record a write: derive the entry and stamp it as updated today."""
    index[get_wiki_key(wiki_dir, page_path)] = derive_entry(wiki_dir, page_path)
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild .wiki-index.json from all wiki pages")
    parser.add_argument("--wiki-dir", default="wiki")
    args = parser.parse_args(argv)

    wiki_dir = Path(args.wiki_dir)
    index = reindex_all(wiki_dir)
    save_index(wiki_dir / ".wiki-index.json", index)
    print(f"reindexed {len(index)} pages")
    return 0
