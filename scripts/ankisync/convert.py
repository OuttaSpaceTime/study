"""Unit conversions between master.db (Prisma/ts-fsrs) and Anki representations."""

from datetime import UTC, datetime, timedelta

# ts-fsrs states; Anki card ctype uses the same numbering.
STATE_NEW, STATE_LEARNING, STATE_REVIEW, STATE_RELEARNING = 0, 1, 2, 3

QUEUE_SUSPENDED = -1
QUEUE_NEW, QUEUE_LEARNING, QUEUE_REVIEW = 0, 1, 2

# Anki's revlog `type`: what the card was when reviewed. Learn covers new and
# learning cards alike, so it reads back as learning; Filtered (a review in a
# filtered deck, often early) as review. Master's Review.state carries it, and a
# rest day's share counts only reviews of Review cards (agentic-spaced-repetition's
# study-ahead.ts), not steps.
REVLOG_LEARN, REVLOG_REVIEW, REVLOG_RELEARN, REVLOG_FILTERED = 0, 1, 2, 3


def revlog_type_to_state(rtype: int) -> int | None:
    """Master's Review.state for a revlog row's type; None for any other (Manual, Rescheduled)."""
    return {
        REVLOG_LEARN: STATE_LEARNING,
        REVLOG_REVIEW: STATE_REVIEW,
        REVLOG_RELEARN: STATE_RELEARNING,
        REVLOG_FILTERED: STATE_REVIEW,
    }.get(rtype)


def state_to_revlog_type(state: int | None) -> int:
    """A revlog type for a master review; Review when the state is unknown, as every push once was."""
    if state in (STATE_NEW, STATE_LEARNING):
        return REVLOG_LEARN
    if state == STATE_RELEARNING:
        return REVLOG_RELEARN
    return REVLOG_REVIEW


def split_tags(tags: str) -> list[str]:
    """Master comma-separated tags -> Anki tag list (no spaces allowed in a tag)."""
    return [t.strip().replace(" ", "_") for t in tags.split(",") if t.strip()]


def state_to_anki(state: int, suspended: bool) -> tuple[int, int]:
    """Map master state -> (anki ctype, anki queue)."""
    ctype = state
    if suspended:
        queue = QUEUE_SUSPENDED
    elif state in (STATE_LEARNING, STATE_RELEARNING):
        queue = QUEUE_LEARNING
    else:
        queue = QUEUE_NEW if state == STATE_NEW else QUEUE_REVIEW
    return ctype, queue


def dt_to_anki_due(due: datetime, state: int, col_crt: datetime) -> int:
    """Master due datetime -> Anki due.

    Review cards: days since collection creation day. Learning cards: epoch seconds.
    """
    if state in (STATE_LEARNING, STATE_RELEARNING):
        return int(due.timestamp())
    return max(0, (due.date() - col_crt.date()).days)


def anki_due_to_dt(due: int, state: int, col_crt: datetime) -> datetime:
    """Inverse of dt_to_anki_due (review cards resolve to 04:00 UTC on the due day)."""
    if state in (STATE_LEARNING, STATE_RELEARNING):
        return datetime.fromtimestamp(due, tz=UTC)
    day = col_crt.date() + timedelta(days=due)
    return datetime(day.year, day.month, day.day, 4, 0, tzinfo=UTC)
