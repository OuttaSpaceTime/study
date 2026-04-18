"""Wiki write orchestrator — updates index, reindexes TreeSearch, embeds via Ollama, runs lint."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from scripts.wiki.embed import update_embeddings
from scripts.wiki.index import load_index, save_index, update_entry
from scripts.wiki.lint import lint_wiki


def wiki_write(page_path: Path, wiki_dir: Path = Path("wiki")) -> dict:
    """Process a wiki page through all stages. Returns JSON-serializable result."""
    page_path = Path(page_path)
    wiki_dir = Path(wiki_dir)
    index_path = wiki_dir / ".wiki-index.json"

    if not page_path.exists():
        return {"status": "error", "message": f"File not found: {page_path}"}

    # Step 1: Parse frontmatter and update index
    index = load_index(index_path)
    index = update_entry(index, wiki_dir, page_path)
    save_index(index_path, index)
    print(f"Index updated: {page_path.relative_to(wiki_dir)}", file=sys.stderr)

    # Step 2: Reindex TreeSearch
    if shutil.which("treesearch"):
        md_files = [
            str(p) for p in wiki_dir.rglob("*.md") if ".obsidian" not in p.parts
        ]
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

    # Step 4: Lint
    errors = lint_wiki(wiki_dir)
    if not errors:
        return {"status": "ok", "lint": "clean"}
    else:
        md_count = len([p for p in wiki_dir.rglob("*.md") if ".obsidian" not in p.parts])
        details = f"lint: {len(errors)} issue(s) found in {md_count} pages:\n\n"
        for err in errors:
            details += f"  \u2717 {err}\n"
        return {"status": "ok", "lint": "errors", "details": details}


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki write orchestrator")
    parser.add_argument("page_path", help="Path to wiki page")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    result = wiki_write(Path(args.page_path), Path(args.wiki_dir))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
