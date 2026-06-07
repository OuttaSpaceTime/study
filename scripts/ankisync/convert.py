"""Unit conversions between master.db (Prisma/ts-fsrs) and Anki representations."""

from datetime import UTC, datetime, timedelta

# ts-fsrs states; Anki card ctype uses the same numbering.
STATE_NEW, STATE_LEARNING, STATE_REVIEW, STATE_RELEARNING = 0, 1, 2, 3

QUEUE_SUSPENDED = -1
QUEUE_NEW, QUEUE_LEARNING, QUEUE_REVIEW = 0, 1, 2


def split_tags(tags: str) -> list[str]:
    """Master comma-separated tags -> Anki tag list (no spaces allowed in a tag)."""
    return [t.strip().replace(" ", "_") for t in tags.split(",") if t.strip()]


def parse_master_dt(value: str | int | float | None) -> datetime | None:
    """Parse Prisma datetimes: ISO-8601 text, or epoch-ms integers (older Prisma)."""
    if value is None:
        return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    return datetime.fromisoformat(value).astimezone(UTC)


def format_master_dt(dt: datetime) -> str:
    """Format a datetime the way Prisma writes them to SQLite."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+00:00"


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
