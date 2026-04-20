"""SRS pressure check — verdict + rendering + CLI.

This script is the single source of truth for SRS state. It shells out to
the flashcard-mcp CLI to fetch due/new counts per deck (accurate, not
truncated like the MCP `get_due_cards` preview) and reads wiki-due from the
wiki index. Skills should call `scripts/srs-pressure --human` (or `--json`)
and rely on its output rather than querying the MCP separately for pressure
signals.

Pressure is always computed globally across all decks — no category filter.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
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

DEFAULT_FLASHCARD_MCP_DIR = Path.home() / "Code" / "Misc" / "flashcard-mcp"

_CHECKS = [
    ("flashcards due", WARN_FLASHCARDS, PAUSE_FLASHCARDS),
    ("wiki pages due", WARN_WIKI, PAUSE_WIKI),
    ("cards already added today", WARN_NEW_TODAY, PAUSE_NEW_TODAY),
]


@dataclass
class DeckState:
    name: str
    total: int
    due: int
    new: int
    learning: int
    review: int


_DECK_HEADER_RE = re.compile(r"^ {2}(?P<name>.+?) \((?P<total>\d+) cards\)\s*$")
_DECK_STATS_RE = re.compile(
    r"^ {4}Due: (?P<due>\d+) \| New: (?P<new>\d+) \| "
    r"Learning: (?P<learning>\d+) \| Review: (?P<review>\d+)\s*$"
)


def parse_decks_output(text: str) -> list[DeckState]:
    """Parse the text output of `flashcard-mcp decks` into DeckState list."""
    decks: list[DeckState] = []
    pending_header: tuple[str, int] | None = None

    for raw in text.splitlines():
        header = _DECK_HEADER_RE.match(raw)
        if header:
            pending_header = (header["name"], int(header["total"]))
            continue
        stats = _DECK_STATS_RE.match(raw)
        if stats and pending_header is not None:
            name, total = pending_header
            decks.append(
                DeckState(
                    name=name,
                    total=total,
                    due=int(stats["due"]),
                    new=int(stats["new"]),
                    learning=int(stats["learning"]),
                    review=int(stats["review"]),
                )
            )
            pending_header = None

    return decks


def fetch_srs_state(mcp_dir: Path | None = None) -> list[DeckState]:
    """Shell out to the flashcard-mcp CLI and parse its decks output."""
    mcp_dir = mcp_dir or Path(os.environ.get("FLASHCARD_MCP_DIR", DEFAULT_FLASHCARD_MCP_DIR))
    result = subprocess.run(
        ["npm", "run", "dev:cli", "--silent", "--", "decks"],
        cwd=str(mcp_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_decks_output(result.stdout)


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


def render_human(
    level: str,
    reasons: list[str],
    flashcards_due: int,
    wiki_due: int,
    new_today: int,
    decks: list[DeckState] | None = None,
) -> str:
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

    if decks:
        lines.append("")
        lines.append("  Decks:")
        for d in decks:
            lines.append(
                f"    {d.name} — {d.due} due "
                f"({d.new} new, {d.learning} learning, {d.review} review)"
            )

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
    parser = argparse.ArgumentParser(description="SRS pressure check — global due across all decks")
    parser.add_argument(
        "--flashcards-due",
        type=int,
        default=None,
        help="Override the due count (by default fetched from flashcard-mcp CLI)",
    )
    parser.add_argument("--new-today", type=int, default=0, help="Cards already added today (optional)")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory (default: wiki)")
    parser.add_argument("--human", action="store_true", help="Print human-readable output instead of JSON")
    args = parser.parse_args(argv)

    decks: list[DeckState] = []
    if args.flashcards_due is None:
        decks = fetch_srs_state()
        flashcards_due = sum(d.due for d in decks)
    else:
        flashcards_due = args.flashcards_due

    wiki_due = wiki_due_count(args.wiki_dir)
    level, reasons = verdict(flashcards_due, wiki_due, args.new_today)

    if args.human:
        print(render_human(level, reasons, flashcards_due, wiki_due, args.new_today, decks))
    else:
        print(json.dumps({
            "verdict": level,
            "flashcards_due": flashcards_due,
            "total_due": flashcards_due,
            "wiki_due": wiki_due,
            "new_today": args.new_today,
            "decks": [asdict(d) for d in decks],
            "reasons": reasons,
            "thresholds": {
                "warn": {"flashcards": WARN_FLASHCARDS, "wiki": WARN_WIKI, "new_today": WARN_NEW_TODAY},
                "pause": {"flashcards": PAUSE_FLASHCARDS, "wiki": PAUSE_WIKI, "new_today": PAUSE_NEW_TODAY},
            },
        }, indent=2))

    return exit_code(level)


if __name__ == "__main__":
    sys.exit(main())
