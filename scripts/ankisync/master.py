"""Read/write access to flashcard-mcp's master.db (SQLite, Prisma-managed).

Reads are read-only connections; writes use short transactions with a busy
timeout so we coexist with the running MCP server (journal_mode=delete).
Only scheduling fields and appended Review rows are ever written — card
existence and content are never modified from the Anki side.
"""

import os
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from scripts.ankisync.convert import format_master_dt, parse_master_dt, split_tags
from scripts.ankisync.merge import AnkiCard, MasterCard, Review, Sched

MASTER_DB = Path(
    os.environ.get("FLASHCARD_MASTER_DB", "~/Code/flashcard-mcp/prisma/master.db")
).expanduser()


def connect(readonly: bool = True) -> sqlite3.Connection:
    if readonly:
        con = sqlite3.connect(f"file:{MASTER_DB}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(MASTER_DB, timeout=10)
        con.execute("PRAGMA busy_timeout = 10000")
    return con


def read_cards(con: sqlite3.Connection) -> list[MasterCard]:
    rows = con.execute(
        """SELECT c.id, c.front, c.back, c.tags, d.name, c.suspended,
                  c.due, c.stability, c.difficulty, c.reps, c.lapses,
                  c.state, c.lastReview, c.interval, c.inheritedFrom
           FROM Card c JOIN Deck d ON d.id = c.deckId"""
    ).fetchall()
    return [
        MasterCard(
            id=r[0],
            front=r[1],
            back=r[2],
            tags=tuple(split_tags(r[3] or "")),
            deck=r[4],
            suspended=bool(r[5]),
            inherited=bool(r[14]),
            sched=Sched(
                due=parse_master_dt(r[6]),
                stability=r[7],
                difficulty=r[8],
                reps=r[9],
                lapses=r[10],
                state=r[11],
                last_review=parse_master_dt(r[12]),
                interval=r[13] or 0.0,
            ),
        )
        for r in rows
    ]


def read_reviews(con: sqlite3.Connection) -> list[Review]:
    rows = con.execute("SELECT cardId, reviewedAt, rating, responseMs FROM Review").fetchall()
    return [
        Review(card_id=r[0], reviewed_at=parse_master_dt(r[1]), rating=r[2], response_ms=r[3])
        for r in rows
    ]


def apply_pull_sched(con: sqlite3.Connection, card_id: str, sched: Sched) -> None:
    """Overwrite a card's scheduling block with the Anki-side winner.

    stability/difficulty keep their current values when Anki has no FSRS memory
    state (e.g. reviews done on a device with FSRS disabled).
    """
    con.execute(
        """UPDATE Card SET due = ?, stability = COALESCE(?, stability),
                  difficulty = COALESCE(?, difficulty), reps = ?,
                  lapses = ?, state = ?, lastReview = ?, interval = ?
           WHERE id = ?""",
        (
            format_master_dt(sched.due) if sched.due else None,
            sched.stability,
            sched.difficulty,
            sched.reps,
            sched.lapses,
            sched.state,
            format_master_dt(sched.last_review) if sched.last_review else None,
            sched.interval,
            card_id,
        ),
    )


def _cuid_like() -> str:
    # Review.id is an app-generated CUID; any unique cuid-shaped string works.
    return "c" + secrets.token_hex(12)


def append_reviews(
    con: sqlite3.Connection, reviews: list[Review], sched_by_card: dict[str, Sched]
) -> int:
    """Append pulled Anki reviews to the Review table.

    stability/difficulty are NOT NULL but Anki's revlog doesn't record FSRS
    snapshots — we store the card's current memory state as an approximation
    (these columns feed analytics only, never scheduling).
    """
    existing = {
        (r[0], int(parse_master_dt(r[1]).timestamp()))
        for r in con.execute("SELECT cardId, reviewedAt FROM Review").fetchall()
    }
    last_seen: dict[str, datetime] = {}
    for card_id, ts in sorted(
        ((r[0], parse_master_dt(r[1])) for r in
         con.execute("SELECT cardId, reviewedAt FROM Review").fetchall()),
        key=lambda x: x[1],
    ):
        last_seen[card_id] = max(last_seen.get(card_id, ts), ts)

    added = 0
    for rev in sorted(reviews, key=lambda r: r.reviewed_at):
        if (rev.card_id, int(rev.reviewed_at.timestamp())) in existing:
            continue
        prev = last_seen.get(rev.card_id)
        elapsed = max(0.0, (rev.reviewed_at - prev).total_seconds() / 86400) if prev else 0.0
        sched = sched_by_card.get(rev.card_id)
        con.execute(
            """INSERT INTO Review (id, cardId, rating, responseMs, stability,
                                   difficulty, elapsedDays, reviewedAt)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                _cuid_like(),
                rev.card_id,
                rev.rating,
                rev.response_ms,
                (sched.stability if sched and sched.stability is not None else 0.0),
                (sched.difficulty if sched and sched.difficulty is not None else 0.0),
                round(elapsed, 6),
                format_master_dt(rev.reviewed_at),
            ),
        )
        last_seen[rev.card_id] = rev.reviewed_at
        added += 1
    return added


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def get_or_create_deck(con: sqlite3.Connection, name: str) -> str:
    """Look up a Deck by name, creating it if this is the first card to land there.

    Used when importing Anki-only cards onto an empty master.db: their deck
    names won't generally match the fixed set of decks a fresh install seeds.
    """
    row = con.execute("SELECT id FROM Deck WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    deck_id = _cuid_like()
    con.execute(
        "INSERT INTO Deck (id, name, createdAt) VALUES (?, ?, ?)",
        (deck_id, name, format_master_dt(now_utc())),
    )
    return deck_id


def import_card(con: sqlite3.Connection, card: AnkiCard) -> None:
    """Insert a Card row recovered from an Anki-only note onto an empty master.db.

    Reuses the Anki note's own guid as the new Card.id: it is already a CUID
    minted by a prior flashcard-mcp instance (that is what made it eligible for
    import rather than being reported as a foreign/unknown note), so identity
    is preserved and no guid rewrite is needed on the Anki side afterward.

    createdAt is derived from the Anki note id (itself an epoch-ms creation
    timestamp), not from the moment of import — these cards are old, and
    check_pressure's newToday axis would otherwise read all of them as added
    today and hard-block further intake for the rest of the day.
    """
    deck_id = get_or_create_deck(con, card.deck)
    sched = card.sched
    now = format_master_dt(now_utc())
    created_at = format_master_dt(datetime.fromtimestamp(card.note_id / 1000, tz=UTC))
    con.execute(
        """INSERT INTO Card (id, deckId, front, back, tags, due, stability,
                              difficulty, reps, lapses, state, lastReview,
                              interval, suspended, createdAt, updatedAt)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            card.guid,
            deck_id,
            card.front,
            card.back,
            ",".join(card.tags),
            format_master_dt(sched.due) if sched.due else now,
            sched.stability or 0.0,
            sched.difficulty or 0.0,
            sched.reps,
            sched.lapses,
            sched.state,
            format_master_dt(sched.last_review) if sched.last_review else None,
            sched.interval,
            int(card.suspended),
            created_at,
            now,
        ),
    )
