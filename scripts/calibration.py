"""Study calibration — true retention, rating discrimination, verdict + CLI.

Answers one question: is /study asking questions at the right difficulty?

Retention is computed the way Anki's true-retention convention defines it,
because the naive "fraction of ratings >= 3 this session" number is inflated
by intra-day relearning repeats and by new cards being acquired rather than
retrieved. Two filters do the work:

- ``elapsed_days >= 1`` drops same-day repeats. A review with no elapsed
  interval is a learning step, not a retrieval test of a scheduled memory.
  The Review table stores no card state, so elapsed interval is the usable
  proxy for "this card was actually due".
- first review per (card, day) keeps a card that lapsed and was re-served
  from being counted twice.

The verdict feeds the difficulty levers in /study Phase 2. It never feeds the
rating rubric: Claude's own ratings produce this number, so letting it move
what counts as correct would make lenient grading the cheapest way to look
calibrated.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta

from scripts.ankisync.convert import parse_master_dt
from scripts.ankisync.master import connect

WINDOW_DAYS = 30
MIN_REVIEWS = 50

OVER_DIFFICULT_BELOW = 0.80
UNDER_DIFFICULT_ABOVE = 0.90
GOOD_SHARE_CEILING = 0.80
MARGIN = 0.02

_RATING_NAMES = {1: "again", 2: "hard", 3: "good", 4: "easy"}


@dataclass(frozen=True)
class ReviewRow:
    card_id: str
    rating: int
    reviewed_at: datetime
    elapsed_days: float


def eligible(rows: list[ReviewRow], window_days: int, now: datetime) -> list[ReviewRow]:
    """Reviews that count toward true retention, oldest first.

    Calendar days are taken in ``now``'s timezone, not UTC. A study day is a
    local day: bucketing a UTC+2 developer's reviews by UTC date would split
    everything before 02:00 local into the previous day, so a lapse and its
    retest would count as two separate days instead of one.
    """
    cutoff = now - timedelta(days=window_days)
    in_window = [r for r in rows if r.reviewed_at >= cutoff and r.elapsed_days >= 1]

    first_per_card_day: dict[tuple[str, str], ReviewRow] = {}
    for r in sorted(in_window, key=lambda r: r.reviewed_at):
        local_day = r.reviewed_at.astimezone(now.tzinfo).date().isoformat()
        first_per_card_day.setdefault((r.card_id, local_day), r)
    return list(first_per_card_day.values())


def rating_mix(rows: list[ReviewRow]) -> dict[str, int]:
    mix = dict.fromkeys(_RATING_NAMES.values(), 0)
    for r in rows:
        mix[_RATING_NAMES[r.rating]] += 1
    return mix


def true_retention(rows: list[ReviewRow]) -> float | None:
    if not rows:
        return None
    return sum(1 for r in rows if r.rating >= 3) / len(rows)


def is_marginal(token: str, retention: float | None) -> bool:
    """True when a retention-derived verdict sits within MARGIN of a band edge.

    The band edges are hard cutoffs applied to a noisy estimator, so a value a
    point outside the band is not evidence of a real difficulty problem. Callers
    use this to soften the lever response instead of flipping it: at 79% the
    verdict is honestly ``over-difficult``, but a single review would move it,
    so switching every lever off would be an overreaction to noise.

    ``low-signal`` is never marginal. That verdict means retention itself is not
    trustworthy yet, so qualifying it by distance-to-a-band-edge would contradict
    the reason it was returned.
    """
    if retention is None or token == "low-signal":
        return False
    return any(
        round(abs(retention - edge), 6) <= MARGIN
        for edge in (OVER_DIFFICULT_BELOW, UNDER_DIFFICULT_ABOVE)
    )


def verdict(rows: list[ReviewRow]) -> tuple[str, list[str]]:
    """Return (token, reasons). Token: over-difficult | calibrated | under-difficult | low-signal."""
    if len(rows) < MIN_REVIEWS:
        return "low-signal", [f"only {len(rows)} eligible reviews (need {MIN_REVIEWS})"]

    mix = rating_mix(rows)
    good_share = mix["good"] / len(rows)
    if good_share > GOOD_SHARE_CEILING:
        return "low-signal", [
            f"poor discrimination: {good_share:.0%} of ratings are Good "
            f"(ceiling {GOOD_SHARE_CEILING:.0%}) — retention is not meaningful until "
            "grading spreads across all four ratings"
        ]

    retention = true_retention(rows)
    if retention < OVER_DIFFICULT_BELOW:
        return "over-difficult", [f"true retention {retention:.0%} (below {OVER_DIFFICULT_BELOW:.0%})"]
    if retention > UNDER_DIFFICULT_ABOVE:
        return "under-difficult", [f"true retention {retention:.0%} (above {UNDER_DIFFICULT_ABOVE:.0%})"]
    return "calibrated", [f"true retention {retention:.0%} (target {OVER_DIFFICULT_BELOW:.0%}-{UNDER_DIFFICULT_ABOVE:.0%})"]


def read_reviews(con: sqlite3.Connection) -> list[ReviewRow]:
    rows = con.execute("SELECT cardId, rating, reviewedAt, elapsedDays FROM Review").fetchall()
    return [ReviewRow(r[0], int(r[1]), parse_master_dt(r[2]), float(r[3])) for r in rows]


def render_human(
    token: str, reasons: list[str], rows: list[ReviewRow], window_days: int, marginal: bool
) -> str:
    retention = true_retention(rows)
    mix = rating_mix(rows)
    headline = "n/a" if retention is None else f"{retention:.0%}"
    lines = [
        f"Calibration: {token.upper()}{' (MARGINAL)' if marginal else ''} — "
        f"true retention {headline} "
        f"(target {OVER_DIFFICULT_BELOW:.0%}-{UNDER_DIFFICULT_ABOVE:.0%})",
        "",
        f"  reviews in window: {len(rows)}  ({window_days}d, first-per-day, elapsed >= 1d)",
        f"  rating mix:        Again {mix['again']} · Hard {mix['hard']} · "
        f"Good {mix['good']} · Easy {mix['easy']}",
        "",
        "Reasons:",
        *(f"  - {r}" for r in reasons),
    ]
    if marginal:
        lines.append(f"  - within {MARGIN:.0%} of the band edge — soften levers, don't switch them off")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Study calibration — true retention and difficulty verdict")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--human", action="store_true", help="Print human-readable output instead of JSON")
    args = parser.parse_args(argv)

    con = connect(readonly=True)
    try:
        rows = eligible(read_reviews(con), args.window_days, datetime.now().astimezone())
    finally:
        con.close()

    token, reasons = verdict(rows)
    retention = true_retention(rows)
    marginal = is_marginal(token, retention)

    if args.human:
        print(render_human(token, reasons, rows, args.window_days, marginal))
    else:
        print(json.dumps({
            "verdict": token,
            "marginal": marginal,
            "true_retention": retention,
            "reviews": len(rows),
            "window_days": args.window_days,
            "rating_mix": rating_mix(rows),
            "reasons": reasons,
            "thresholds": {
                "min_reviews": MIN_REVIEWS,
                "over_difficult_below": OVER_DIFFICULT_BELOW,
                "under_difficult_above": UNDER_DIFFICULT_ABOVE,
                "good_share_ceiling": GOOD_SHARE_CEILING,
            },
        }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
