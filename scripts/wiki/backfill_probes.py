"""Backfill `probe_sections` + `last_probed` for existing SRS-tracked wiki pages.

Default: all H2s are probe-worthy except Related Concepts, References, See also, TL;DR.
Seeds `last_probed` equal to `probe_sections` so the queue invariant holds from day one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.wiki.frontmatter import (
    dump_page,
    extract_h2s,
    normalize_heading,
    parse_frontmatter,
)
from scripts.wiki.index import iter_wiki_pages, load_index, save_index, update_entry

EXCLUDED_HEADINGS = {
    normalize_heading(h)
    for h in ("Related Concepts", "References", "See also", "TL;DR")
}


def eligible_h2s(body: str) -> list[str]:
    """Return H2 headings from body, excluding the reference-only set."""
    return [h for h in extract_h2s(body) if normalize_heading(h) not in EXCLUDED_HEADINGS]


def backfill_page(page_path: Path, dry_run: bool = False) -> dict:
    """Backfill one page. Returns status dict.

    Statuses:
      - added: probe_sections written.
      - would-add: dry-run, no change.
      - skipped: probe_sections already present and non-empty.
      - no-eligible-h2s: all H2s are in the excluded set (or none exist).
      - no-frontmatter: page has no YAML frontmatter.
    """
    meta, body = parse_frontmatter(page_path.read_text())
    if not meta:
        return {"status": "no-frontmatter", "file": str(page_path)}

    if meta.get("probe_sections"):
        return {"status": "skipped", "file": str(page_path)}

    sections = eligible_h2s(body)
    if not sections:
        return {"status": "no-eligible-h2s", "file": str(page_path)}

    if dry_run:
        return {"status": "would-add", "file": str(page_path), "probe_sections": sections}

    meta["probe_sections"] = sections
    meta["last_probed"] = list(sections)
    page_path.write_text(dump_page(meta, body))
    return {"status": "added", "file": str(page_path), "probe_sections": sections}


def backfill_wiki(wiki_dir: Path, dry_run: bool = False) -> list[dict]:
    results = [backfill_page(p, dry_run=dry_run) for p in iter_wiki_pages(wiki_dir)]

    # Only the index needs syncing — body is unchanged, so embeddings / TreeSearch don't.
    if not dry_run and any(r["status"] == "added" for r in results):
        index_path = wiki_dir / ".wiki-index.json"
        index = load_index(index_path)
        for r in results:
            if r["status"] == "added":
                update_entry(index, wiki_dir, Path(r["file"]))
        save_index(index_path, index)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill probe_sections for SRS-tracked wiki pages"
    )
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    results = backfill_wiki(wiki_dir, dry_run=args.dry_run)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        if r["status"] in ("added", "would-add", "no-eligible-h2s"):
            extra = (
                f" → {r.get('probe_sections')}"
                if r.get("probe_sections") is not None
                else ""
            )
            print(f"{r['status']}: {r['file']}{extra}")

    print()
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    print(f"backfill summary: {summary}")

    if counts.get("no-eligible-h2s", 0) > 0:
        print(
            "warning: some pages had no eligible H2s — author probe_sections manually.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
