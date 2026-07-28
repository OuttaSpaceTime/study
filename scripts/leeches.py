"""Leech candidates — cards whose repeated failure means the card is the problem.

Only the candidate list lives here. Which leech a session actually raises depends
on which cards were served, which no preflight can know, so that selection stays
in /study Phase 2. The ordering below encodes the tie-break, so Phase 2 walks this
list in order rather than re-deriving it.

Suspended cards are dropped: they keep their lapse count but are not in review, so
flagging one fixes nothing the developer is about to hit.
"""

from __future__ import annotations

import argparse
import json
import sys
from math import inf

from scripts.ankisync.master import connect, read_cards
from scripts.ankisync.merge import MasterCard

LEECH_THRESHOLD = 5
FRONT_DISPLAY_CHARS = 80


def leeches(cards: list[MasterCard], threshold: int = LEECH_THRESHOLD) -> list[MasterCard]:
    """Flagged cards, most urgent first: lapses descending, then weakest memory."""
    flagged = [c for c in cards if c.sched.lapses >= threshold and not c.suspended]
    return sorted(
        flagged,
        key=lambda c: (-c.sched.lapses, inf if c.sched.stability is None else c.sched.stability),
    )


def render_human(rows: list[MasterCard], threshold: int) -> str:
    if not rows:
        return f"Leeches: none — no card at {threshold}+ lapses"
    lines = [f"Leeches: {len(rows)} at {threshold}+ lapses, most urgent first", ""]
    for i, c in enumerate(rows, 1):
        stability = "n/a" if c.sched.stability is None else f"{c.sched.stability:.1f}"
        lines.append(f"{i}. [{c.sched.lapses} lapses · stability {stability}] {c.front[:FRONT_DISPLAY_CHARS]}")
        lines.append(f"   {c.id} · {c.deck}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Leech candidates — cards at or above the lapse threshold")
    parser.add_argument("--threshold", type=int, default=LEECH_THRESHOLD)
    parser.add_argument("--human", action="store_true", help="Print human-readable output instead of JSON")
    args = parser.parse_args(argv)

    con = connect(readonly=True)
    try:
        rows = leeches(read_cards(con), args.threshold)
    finally:
        con.close()

    if args.human:
        print(render_human(rows, args.threshold))
    else:
        print(json.dumps([
            {
                "card_id": c.id,
                "front": c.front,
                "deck": c.deck,
                "lapses": c.sched.lapses,
                "stability": c.sched.stability,
            }
            for c in rows
        ], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
