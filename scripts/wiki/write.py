"""Wiki write orchestrator — updates index, reindexes TreeSearch, embeds via Ollama, runs lint."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from scripts.wiki.embed import update_embeddings
from scripts.wiki.frontmatter import dump_page, parse_frontmatter
from scripts.wiki.index import iter_wiki_pages, load_index, save_index, update_entry
from scripts.wiki.lint import lint_wiki

_DEFAULT_REVIEW_INTERVAL = 3


def _fill_defaults(page_path: Path, meta: dict) -> bool:
    """Add default values for any missing required fields. Mutates meta; returns True iff changed."""
    changed = False

    if "flashcard_ids" not in meta:
        meta["flashcard_ids"] = []
        changed = True

    if _seed_last_probed(meta):
        changed = True

    if page_path.stem.endswith("-index"):
        return changed

    if "depth" not in meta:
        meta["depth"] = 1
        changed = True

    if "review_interval" not in meta:
        meta["review_interval"] = _DEFAULT_REVIEW_INTERVAL
        changed = True

    if "next_review" not in meta:
        meta["next_review"] = (date.today() + timedelta(days=_DEFAULT_REVIEW_INTERVAL)).isoformat()
        changed = True

    return changed


def _seed_last_probed(meta: dict) -> bool:
    """Seed last_probed from probe_sections when missing. Mutates meta; returns True iff changed."""
    if "last_probed" in meta:
        return False
    probe_sections = meta.get("probe_sections")
    if not probe_sections:
        return False
    meta["last_probed"] = list(probe_sections)
    return True


def _moc_path(wiki_dir: Path, folder: str) -> Path:
    return wiki_dir / folder / f"{folder}-index.md"


def update_moc(page_path: Path, wiki_dir: Path) -> bool:
    """Rebuild the folder MOC's `## Pages` from the filesystem. Returns True iff the MOC changed."""
    page_path = Path(page_path)
    wiki_dir = Path(wiki_dir)

    if page_path.parent.parent != wiki_dir:
        return False

    folder = page_path.parent.name
    moc = _moc_path(wiki_dir, folder)
    if not moc.exists():
        print(f"Warning: no MOC for folder '{folder}' — create {moc.relative_to(wiki_dir.parent)}", file=sys.stderr)
        return False

    slugs = sorted(p.stem for p in (wiki_dir / folder).glob("*.md") if p.name != moc.name)
    moc_meta, moc_body = parse_frontmatter(moc.read_text())

    lines = moc_body.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## Pages"), None)
    if start is None:
        raise ValueError(f"MOC {moc} has no '## Pages' section")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))

    new_block = [lines[start], ""] + [f"- [[{folder}/{s}]]" for s in slugs] + [""]
    rebuilt_body = "\n".join(lines[:start] + new_block + lines[end:])
    if moc_body.endswith("\n"):
        rebuilt_body += "\n"

    if rebuilt_body == moc_body:
        return False

    moc_meta["updated"] = date.today().isoformat()
    moc.write_text(dump_page(moc_meta, rebuilt_body))
    return True


def wiki_write(page_path: Path, wiki_dir: Path = Path("wiki")) -> dict:
    """Process a wiki page through all stages. Returns JSON-serializable result."""
    page_path = Path(page_path)
    wiki_dir = Path(wiki_dir)
    index_path = wiki_dir / ".wiki-index.json"

    if not page_path.exists():
        return {"status": "error", "message": f"File not found: {page_path}"}

    # Step 1: Fill missing-field defaults, then update index
    meta, body = parse_frontmatter(page_path.read_text())
    if _fill_defaults(page_path, meta):
        page_path.write_text(dump_page(meta, body))
        print(f"Defaults filled: {page_path.relative_to(wiki_dir)}", file=sys.stderr)

    index = load_index(index_path)
    index = update_entry(index, wiki_dir, page_path)
    save_index(index_path, index)
    print(f"Index updated: {page_path.relative_to(wiki_dir)}", file=sys.stderr)

    # Step 2: Reindex TreeSearch
    if shutil.which("treesearch"):
        md_files = [str(p) for p in iter_wiki_pages(wiki_dir)]
        if md_files:
            subprocess.run(
                ["treesearch", "index", "--paths", *md_files, "-o", str(wiki_dir / "indexes"), "--force"],
                capture_output=True,
            )
        print("TreeSearch reindexed", file=sys.stderr)
    else:
        print("Warning: treesearch not found, skipping reindex", file=sys.stderr)

    # Step 3: Embed via Ollama
    try:
        import urllib.request

        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        update_embeddings(wiki_dir, page_path)
        rel_key = str(page_path.relative_to(wiki_dir)).removesuffix(".md")
        print(f"Embedded: {rel_key}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: Ollama not available, skipping embedding: {e}", file=sys.stderr)

    # Step 3b: Auto-update folder MOC (reindex only if changed)
    try:
        if update_moc(page_path, wiki_dir):
            moc = _moc_path(wiki_dir, page_path.parent.name)
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
