"""Query wiki entries due for review."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.wiki.index import load_index

FOLDER_TITLE_OVERRIDES = {
    "sql": "SQL",
    "llm": "LLM",
    "json-api": "JSON API",
    "openapi": "OpenAPI",
    "typescript": "TypeScript",
}


def display_title(key: str, title: str) -> str:
    """Render a wiki key + title as a readable breadcrumb, e.g. 'Rails/Routing: Collection and Member Routes'."""
    folders = key.split("/")[:-1]
    parts = [
        FOLDER_TITLE_OVERRIDES.get(folder, folder.replace("-", " ").title())
        for folder in folders
    ]
    return f"{'/'.join(parts)}: {title}"


def get_due_entries(
    index: dict, today: str | None = None
) -> list[dict]:
    """Return index entries where next_review <= today, sorted most overdue first."""
    if today is None:
        today = date.today().isoformat()

    due = []
    for key, entry in index.items():
        nr = entry.get("next_review")
        if not nr:
            continue
        if nr > today:
            continue
        tags = entry.get("tags") or []
        if "moc" in tags:
            continue
        due.append(
            {
                "key": key,
                "file": entry.get("file", ""),
                "title": entry.get("title", ""),
                "next_review": nr,
                "review_interval": entry.get("review_interval"),
                "tags": entry.get("tags", []),
            }
        )

    due.sort(key=lambda e: e["next_review"])
    return due


def main() -> None:
    parser = argparse.ArgumentParser(description="Query wiki entries due for review")
    parser.add_argument("--count", action="store_true", help="Print count only")
    parser.add_argument("--human", action="store_true", help="Human-readable numbered list")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    index_path = Path(args.wiki_dir) / ".wiki-index.json"
    index = load_index(index_path)
    due = get_due_entries(index)

    if args.count:
        print(len(due))
    elif args.human:
        for i, entry in enumerate(due, 1):
            interval = entry.get("review_interval", "?")
            due_date = entry.get("next_review", "?")
            print(f"{i}. {display_title(entry['key'], entry['title'])} — due {due_date} (interval: {interval}d)")
    else:
        print(json.dumps(due, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
