"""Wiki write orchestrator — updates index, refreshes the qmd search index, runs lint.

`--all` rebuilds the whole index instead of processing one page (see `reindex_all`).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.wiki.frontmatter import dump_page, parse_frontmatter
from scripts.wiki.index import (
    iter_wiki_pages,
    load_index,
    reindex_all,
    save_index,
    update_entry,
)
from scripts.wiki.lint import lint_wiki


def _ensure_flashcard_ids(meta: dict) -> bool:
    """Add flashcard_ids if missing. Mutates meta; returns True iff changed."""
    if "flashcard_ids" in meta:
        return False
    meta["flashcard_ids"] = []
    return True


def wiki_write(page_path: Path, wiki_dir: Path = Path("wiki")) -> dict:
    """Process a wiki page through all stages. Returns JSON-serializable result."""
    page_path = Path(page_path)
    wiki_dir = Path(wiki_dir)
    index_path = wiki_dir / ".wiki-index.json"

    if not page_path.exists():
        return {"status": "error", "message": f"File not found: {page_path}"}

    # Step 1: Backfill flashcard_ids, then update index
    meta, body = parse_frontmatter(page_path.read_text())
    if _ensure_flashcard_ids(meta):
        page_path.write_text(dump_page(meta, body))
        print(f"flashcard_ids added: {page_path.relative_to(wiki_dir)}", file=sys.stderr)

    index = load_index(index_path)
    index = update_entry(index, wiki_dir, page_path)
    save_index(index_path, index)
    print(f"Index updated: {page_path.relative_to(wiki_dir)}", file=sys.stderr)

    # Step 2: Refresh qmd search index (BM25 + vector embeddings)
    if shutil.which("qmd"):
        subprocess.run(["qmd", "update"], capture_output=True)
        subprocess.run(["qmd", "embed"], capture_output=True)
        print("qmd index refreshed", file=sys.stderr)
    else:
        print("Warning: qmd not found, skipping search reindex", file=sys.stderr)

    # Step 3: Lint
    errors, warnings = lint_wiki(wiki_dir)
    if not errors and not warnings:
        return {"status": "ok", "lint": "clean"}
    md_count = len(iter_wiki_pages(wiki_dir))
    summary_parts = []
    if errors:
        summary_parts.append(f"{len(errors)} error(s)")
    if warnings:
        summary_parts.append(f"{len(warnings)} warning(s)")
    details = f"lint: {', '.join(summary_parts)} in {md_count} pages:\n\n"
    for err in errors:
        details += f"  \u2717 {err}\n"
    for warn in warnings:
        details += f"  \u26a0 {warn}\n"
    status = "errors" if errors else "warnings"
    return {"status": "ok", "lint": status, "details": details}


def rebuild_index(wiki_dir: Path = Path("wiki")) -> int:
    """Rebuild .wiki-index.json from every page on disk; returns the page count.

    A derive, not a write: no qmd refresh and no lint, and each page keeps its
    `updated` stamp. Use it after an index schema change or after pages moved.
    """
    wiki_dir = Path(wiki_dir)
    index = reindex_all(wiki_dir)
    save_index(wiki_dir / ".wiki-index.json", index)
    return len(index)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki write orchestrator")
    parser.add_argument("page_path", nargs="?", help="Path to wiki page")
    parser.add_argument(
        "--all", action="store_true", help="Rebuild .wiki-index.json from every page instead"
    )
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    if args.all:
        if args.page_path:
            parser.error("--all takes no page path")
        print(f"reindexed {rebuild_index(Path(args.wiki_dir))} pages")
        return
    if not args.page_path:
        parser.error("a page path is required (or --all)")

    result = wiki_write(Path(args.page_path), Path(args.wiki_dir))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
