"""Archive or unarchive a wiki page by toggling its `archived` tag.

An archived page keeps its place, frontmatter, and schedule, but the
`archived` tag drops it from wiki review (`get_due_entries` skips it, so it
leaves both `scripts/wiki-due` and the SRS pressure count) and from the
Obsidian graph (which filters `-tag:#archived`). Reversible: unarchive
removes the tag and the page rejoins review at its stored `next_review`.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.wiki.frontmatter import dump_page, parse_frontmatter

ARCHIVED_TAG = "archived"


def set_archived(meta: dict, archive: bool) -> bool:
    """Add or remove the `archived` tag in-place. Returns True if tags changed."""
    tags = meta.get("tags", [])
    if not isinstance(tags, list):
        tags = [tags]

    has = ARCHIVED_TAG in tags
    if archive and not has:
        tags = tags + [ARCHIVED_TAG]
    elif not archive and has:
        tags = [t for t in tags if t != ARCHIVED_TAG]
    else:
        return False

    meta["tags"] = tags
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive or unarchive a wiki page")
    parser.add_argument("page_path", help="Path to wiki page")
    parser.add_argument(
        "--unarchive", action="store_true", help="Remove the archived tag instead of adding it"
    )
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    page_path = Path(args.page_path)
    if not page_path.exists():
        print(f"No such page: {page_path}", file=sys.stderr)
        sys.exit(1)

    meta, body = parse_frontmatter(page_path.read_text())
    verb = "Unarchived" if args.unarchive else "Archived"

    if not set_archived(meta, archive=not args.unarchive):
        print(f"No change: {page_path} already {'un' if args.unarchive else ''}archived")
        return

    page_path.write_text(dump_page(meta, body))

    write_script = Path(__file__).resolve().parent.parent / "wiki-write"
    subprocess.run(
        [str(write_script), str(page_path), "--wiki-dir", args.wiki_dir], check=True
    )
    print(f"{verb} {page_path}")


if __name__ == "__main__":
    main()
