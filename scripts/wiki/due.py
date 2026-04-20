"""Query wiki entries due for review."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.wiki.index import load_index


def get_due_entries(
    index: dict, today: str | None = None, category: str | None = None
) -> list[dict]:
    """Return index entries where next_review <= today, sorted most overdue first.

    If `category` is given, only entries with matching `category` are returned.
    """
    if today is None:
        today = date.today().isoformat()

    due = []
    for key, entry in index.items():
        nr = entry.get("next_review")
        if not nr:
            continue
        if nr > today:
            continue
        if category is not None and entry.get("category") != category:
            continue
        due.append(
            {
                "key": key,
                "file": entry.get("file", ""),
                "title": entry.get("title", ""),
                "category": entry.get("category"),
                "next_review": nr,
                "review_interval": entry.get("review_interval"),
                "tags": entry.get("tags", []),
                "sections": entry.get("sections", []),
            }
        )

    due.sort(key=lambda e: e["next_review"])
    return due


def main() -> None:
    parser = argparse.ArgumentParser(description="Query wiki entries due for review")
    parser.add_argument("--count", action="store_true", help="Print count only")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    parser.add_argument(
        "--category",
        choices=["work", "personal"],
        default=None,
        help="Filter to a single category",
    )
    args = parser.parse_args()

    index_path = Path(args.wiki_dir) / ".wiki-index.json"
    index = load_index(index_path)
    due = get_due_entries(index, category=args.category)

    if args.count:
        print(len(due))
    else:
        print(json.dumps(due, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
