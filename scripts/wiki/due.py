"""Query wiki entries due for review."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from scripts.wiki.index import load_index


def get_due_entries(index: dict, today: str | None = None) -> list[dict]:
    """Return index entries where next_review <= today, sorted most overdue first."""
    if today is None:
        today = date.today().isoformat()

    due = []
    for key, entry in index.items():
        nr = entry.get("next_review")
        if not nr:
            continue
        if nr <= today:
            due.append(
                {
                    "key": key,
                    "file": entry.get("file", ""),
                    "title": entry.get("title", ""),
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
    args = parser.parse_args()

    index_path = Path(args.wiki_dir) / ".wiki-index.json"
    index = load_index(index_path)
    due = get_due_entries(index)

    if args.count:
        print(len(due))
    else:
        print(json.dumps(due, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
