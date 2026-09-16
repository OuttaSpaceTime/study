"""Wiki write orchestrator — updates index, refreshes the qmd search index, runs lint."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from scripts.wiki.frontmatter import dump_page, parse_frontmatter
from scripts.wiki.index import iter_wiki_pages, load_index, save_index, update_entry
from scripts.wiki.lint import lint_wiki


def _ensure_flashcard_ids(meta: dict) -> bool:
    """Add flashcard_ids if missing. Mutates meta; returns True iff changed."""
    if "flashcard_ids" in meta:
        return False
    meta["flashcard_ids"] = []
    return True


def _moc_path_for_folder(folder_path: Path) -> Path:
    """Return the conventional MOC path for a folder: <folder>/<folder>-index.md."""
    return folder_path / f"{folder_path.name}-index.md"


def _moc_entries_for_folder(folder_path: Path, wiki_dir: Path) -> list[str]:
    """Return the wikilink targets for a folder's MOC `## Pages` section.

    Top-level folder: sub-MOCs (sorted) followed by loose top-level pages (sorted).
    Sub-folder: direct children only (sorted).
    """
    rel_parts = folder_path.relative_to(wiki_dir).parts
    moc_name = f"{folder_path.name}-index.md"

    direct_pages = sorted(
        p.stem for p in folder_path.glob("*.md") if p.name != moc_name
    )

    if len(rel_parts) == 1:
        sub_mocs = []
        for sub_dir in sorted(d for d in folder_path.iterdir() if d.is_dir()):
            sub_moc = _moc_path_for_folder(sub_dir)
            if sub_moc.exists():
                sub_mocs.append(f"{sub_dir.name}/{sub_dir.name}-index")
        return [f"{folder_path.name}/{e}" for e in sub_mocs] + [
            f"{folder_path.name}/{s}" for s in direct_pages
        ]

    # Sub-folder: prefix is "<top>/<sub>/"
    prefix = "/".join(rel_parts)
    return [f"{prefix}/{s}" for s in direct_pages]


def _rebuild_moc(moc_path: Path, wiki_dir: Path) -> bool:
    """Rebuild a MOC's `## Pages` section from the filesystem. Returns True iff it changed."""
    if not moc_path.exists():
        return False
    moc_meta, moc_body = parse_frontmatter(moc_path.read_text())
    folder_path = moc_path.parent
    entries = _moc_entries_for_folder(folder_path, wiki_dir)

    lines = moc_body.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Pages"), None)
    if start is None:
        raise ValueError(f"MOC {moc_path} has no '## Pages' section")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))

    new_block = [lines[start], ""] + [f"- [[{e}]]" for e in entries] + [""]
    rebuilt_body = "\n".join(lines[:start] + new_block + lines[end:])
    if moc_body.endswith("\n"):
        rebuilt_body += "\n"

    if rebuilt_body == moc_body:
        return False

    moc_meta["updated"] = date.today().isoformat()
    moc_path.write_text(dump_page(moc_meta, rebuilt_body))
    return True


def update_moc(page_path: Path, wiki_dir: Path) -> list[Path]:
    """Rebuild the folder MOC(s) affected by writing page_path.

    Returns the list of MOC paths that actually changed. Supports one level of nesting:
    a write inside a sub-folder rebuilds both the sub-MOC and the parent top-level MOC,
    so the parent picks up a brand-new sub-MOC on its first write.
    """
    page_path = Path(page_path)
    wiki_dir = Path(wiki_dir)

    try:
        rel_parts = page_path.relative_to(wiki_dir).parts
    except ValueError:
        return []

    # rel_parts: (<folder>, <file>) or (<folder>, <sub>, <file>)
    if len(rel_parts) not in (2, 3):
        return []

    affected_folders: list[Path] = [page_path.parent]
    if len(rel_parts) == 3:
        affected_folders.append(page_path.parent.parent)

    changed: list[Path] = []
    for folder_path in affected_folders:
        moc = _moc_path_for_folder(folder_path)
        if not moc.exists():
            print(
                f"Warning: no MOC for folder '{folder_path.relative_to(wiki_dir)}' — "
                f"create {moc.relative_to(wiki_dir.parent)}",
                file=sys.stderr,
            )
            continue
        if _rebuild_moc(moc, wiki_dir):
            changed.append(moc)
    return changed


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

    # Step 3b: Auto-update folder MOC(s) — sub-MOC first, then parent.
    try:
        for moc in update_moc(page_path, wiki_dir):
            if moc != page_path:
                index = update_entry(index, wiki_dir, moc)
                save_index(index_path, index)
    except (OSError, ValueError) as e:
        print(f"Warning: MOC update failed ({type(e).__name__}): {e}", file=sys.stderr)

    # Step 4: Lint
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki write orchestrator")
    parser.add_argument("page_path", help="Path to wiki page")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    result = wiki_write(Path(args.page_path), Path(args.wiki_dir))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
