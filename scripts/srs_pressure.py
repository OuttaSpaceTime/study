"""SRS pressure check — verdict + rendering + CLI.

Flashcard counts must be passed in (MCP is the source of truth and can only
be queried from inside Claude Code). Wiki-due count is read from the index.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.wiki.due import get_due_entries
from scripts.wiki.index import load_index

PAUSE_FLASHCARDS = 50
PAUSE_WIKI = 20
PAUSE_NEW_TODAY = 10

WARN_FLASHCARDS = 20
WARN_WIKI = 8
WARN_NEW_TODAY = 5

_LEVEL_ORDER = {"ok": 0, "warn": 1, "pause": 2}

EXIT_OK = 0
EXIT_WARN = 1
EXIT_PAUSE = 2


_CHECKS = [
    ("flashcards due", WARN_FLASHCARDS, PAUSE_FLASHCARDS),
    ("wiki pages due", WARN_WIKI, PAUSE_WIKI),
    ("cards already added today", WARN_NEW_TODAY, PAUSE_NEW_TODAY),
]


def verdict(flashcards_due: int, wiki_due: int, new_today: int) -> tuple[str, list[str]]:
    """Return (level, reasons). Level is one of: ok, warn, pause."""
    reasons: list[str] = []
    level = "ok"

    for count, (label, warn, pause) in zip((flashcards_due, wiki_due, new_today), _CHECKS, strict=True):
        if count >= pause:
            reasons.append(f"{count} {label} (>= {pause})")
            new_level = "pause"
        elif count >= warn:
            reasons.append(f"{count} {label}")
            new_level = "warn"
        else:
            continue
        if _LEVEL_ORDER[new_level] > _LEVEL_ORDER[level]:
            level = new_level

    return level, reasons


def exit_code(level: str) -> int:
    return {"ok": EXIT_OK, "warn": EXIT_WARN, "pause": EXIT_PAUSE}[level]


def render_human(level: str, reasons: list[str], flashcards_due: int, wiki_due: int, new_today: int) -> str:
    header = {
        "ok": "SRS pressure: OK",
        "warn": "We recommend pausing.",
        "pause": "Danger! You are well past the recommended pause point.",
    }[level]

    lines = [
        header,
        "",
        f"  flashcards due:    {flashcards_due}",
        f"  wiki pages due:    {wiki_due}",
        f"  cards added today: {new_today}",
    ]

    if level == "ok":
        return "\n".join(lines)

    lines.append("")
    lines.append("Reasons:")
    lines.extend(f"  - {r}" for r in reasons)
    lines.append("")
    lines.append(
        "When learning, we retain more knowledge from short, focused daily\n"
        "review sessions than from adding more material on top of a review\n"
        "backlog. Cramming makes it easier to get in over your head and\n"
        "increases daily reviews, which may feel like a burden.\n\n"
        "Recommendation: clear some review load first (/study, scripts/wiki-due),\n"
        "then come back to add new content. You can continue if you accept\n"
        "the downsides."
    )
    return "\n".join(lines)


def wiki_due_count(wiki_dir: str | Path) -> int:
    index_path = Path(wiki_dir) / ".wiki-index.json"
    return len(get_due_entries(load_index(index_path)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SRS pressure check before adding new content")
    parser.add_argument("--flashcards-due", type=int, required=True, help="Count of flashcards due now (from MCP get_due_cards)")
    parser.add_argument("--new-today", type=int, default=0, help="Cards already added today (from MCP, optional)")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory (default: wiki)")
    parser.add_argument("--human", action="store_true", help="Print human-readable warning instead of JSON")
    args = parser.parse_args(argv)

    wiki_due = wiki_due_count(args.wiki_dir)
    level, reasons = verdict(args.flashcards_due, wiki_due, args.new_today)

    if args.human:
        print(render_human(level, reasons, args.flashcards_due, wiki_due, args.new_today))
    else:
        print(json.dumps({
            "verdict": level,
            "flashcards_due": args.flashcards_due,
            "wiki_due": wiki_due,
            "new_today": args.new_today,
            "reasons": reasons,
            "thresholds": {
                "warn": {"flashcards": WARN_FLASHCARDS, "wiki": WARN_WIKI, "new_today": WARN_NEW_TODAY},
                "pause": {"flashcards": PAUSE_FLASHCARDS, "wiki": PAUSE_WIKI, "new_today": PAUSE_NEW_TODAY},
            },
        }, indent=2))

    return exit_code(level)


if __name__ == "__main__":
    sys.exit(main())
