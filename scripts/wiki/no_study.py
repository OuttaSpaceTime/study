"""Exclude a wiki page from the study loop by toggling its `no-study` tag.

A `no-study` page keeps its place, frontmatter, and schedule; the tag drops
it from the study loop *only* (`get_due_entries` skips it, so it leaves both
`scripts/wiki-due` and the SRS pressure count). It stays a full member of the
wiki otherwise: in the graph, page list, search, and index. Reversible:
`--include` removes the tag and the page rejoins review at its stored
`next_review`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.wiki.frontmatter import dump_page, parse_frontmatter

NO_STUDY_TAG = "no-study"


def set_no_study(meta: dict, exclude: bool) -> bool:
    """Add or remove the `no-study` tag in-place. Returns True if tags changed."""
    tags = meta.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags]

    has = NO_STUDY_TAG in tags
    if exclude and not has:
        tags = tags + [NO_STUDY_TAG]
    elif not exclude and has:
        tags = [t for t in tags if t != NO_STUDY_TAG]
    else:
        return False

    meta["tags"] = tags
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exclude a wiki page from the study loop (or --include it back)"
    )
    parser.add_argument("page_path", help="Path to wiki page")
    parser.add_argument(
        "--include",
        action="store_true",
        help="Remove the no-study tag instead of adding it (rejoin the study loop)",
    )
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    page_path = Path(args.page_path)
    if not page_path.exists():
        print(f"No such page: {page_path}", file=sys.stderr)
        sys.exit(1)

    meta, body = parse_frontmatter(page_path.read_text())
    verb = "Included in study loop" if args.include else "Excluded from study loop"

    if not set_no_study(meta, exclude=not args.include):
        state = "in the study loop" if args.include else "excluded from study"
        print(f"No change: {page_path} already {state}")
        return

    page_path.write_text(dump_page(meta, body))

    write_script = Path(__file__).resolve().parent.parent / "wiki-write"
    subprocess.run(
        [str(write_script), str(page_path), "--wiki-dir", args.wiki_dir], check=True
    )
    print(f"{verb}: {page_path}")


if __name__ == "__main__":
    main()
