"""The adapter between merge.py's dataclasses and the deck client.

master.db belongs to flashcard-mcp, so nothing here opens it: cards, reviews and
tombstones are read through `DeckClient`, and everything a sync decided to write goes
out as one `syncApply` call, which flashcard-mcp applies in one transaction under its
own rules (the cascade and tombstone on a delete, the fallback memory state for a card
Anki never computed FSRS for, the content rules on an import, whole-second review
dedupe). The sync decides what to write; this only translates it.
"""

from datetime import UTC, datetime

from scripts.ankisync.convert import split_tags
from scripts.ankisync.merge import AnkiCard, HistoryPlan, MasterCard, Review, Sched, SyncPlan
from scripts.deck.client import CardRecord, DeckClient, iso

# A plan that imports many cards is one transaction the server may spend a while on.
SYNC_APPLY_TIMEOUT = 300


def _master_card(r: CardRecord) -> MasterCard:
    return MasterCard(
        id=r.id,
        front=r.front,
        back=r.back,
        tags=tuple(split_tags(",".join(r.tags))),
        deck=r.deck,
        suspended=r.suspended,
        inherited=bool(r.inherited_from),
        exercise=r.exercise or "",
        sched=Sched(
            due=r.due,
            stability=r.stability,
            difficulty=r.difficulty,
            reps=r.reps,
            lapses=r.lapses,
            state=r.state,
            last_review=r.last_review,
            interval=r.interval or 0.0,
        ),
    )


def read_cards(deck: DeckClient) -> list[MasterCard]:
    return [_master_card(r) for r in deck.card_records()]


def read_reviews(deck: DeckClient) -> list[Review]:
    return [
        Review(card_id=r.card_id, reviewed_at=r.reviewed_at, rating=r.rating, response_ms=r.response_ms, state=r.state)
        for r in deck.review_records()
    ]


def read_tombstones(deck: DeckClient) -> set[str]:
    """Card ids deleted here."""
    return deck.tombstones()


def _sched_wire(sched: Sched) -> dict:
    return {
        "due": iso(sched.due) if sched.due else None,
        "stability": sched.stability,
        "difficulty": sched.difficulty,
        "reps": sched.reps,
        "lapses": sched.lapses,
        "state": sched.state,
        "lastReview": iso(sched.last_review) if sched.last_review else None,
        "interval": sched.interval,
    }


def _import_wire(card: AnkiCard) -> dict:
    """A card seen only in Anki, under the note's own guid (a CUID this deck minted, so identity survives).

    createdAt comes from the Anki note id, itself an epoch-ms creation time: these cards are
    old, and the deck's "added today" pressure axis would otherwise read every import as new
    intake and block further cards for the day.
    """
    return {
        "id": card.guid,
        "deck": card.deck,
        "front": card.front,
        "back": card.back,
        "tags": list(card.tags),
        "exercise": card.exercise or None,
        "suspended": card.suspended,
        "createdAt": iso(datetime.fromtimestamp(card.note_id / 1000, tz=UTC)),
        **_sched_wire(card.sched),
    }


def _review_wire(rev: Review) -> dict:
    # stability/difficulty are left out: Anki's revlog has no FSRS snapshot, and the deck
    # falls back to the card's incoming schedule or import from the same call.
    return {
        "cardId": rev.card_id,
        "reviewedAt": iso(rev.reviewed_at),
        "rating": rev.rating,
        "responseMs": rev.response_ms,
        "state": rev.state,
    }


def apply_plan(deck: DeckClient, plan: SyncPlan, hist: HistoryPlan) -> dict:
    """Everything the plan writes to the deck, as one `syncApply` call; returns its result.

    A plan with nothing for the deck makes no call: most runs are only pushes to Anki.
    """
    writes = {
        "imports": [_import_wire(a) for a in plan.import_from_anki],
        "deletions": [a.guid for a in plan.local_soft_delete],
        "schedules": [{"cardId": card_id, **_sched_wire(sched)} for card_id, sched in plan.pull_sched],
        "reviews": [_review_wire(r) for r in hist.pull_reviews],
    }
    if not any(writes.values()):
        return {"imports": {"imported": 0, "rejected": []}}
    return deck.sync_apply(**writes, timeout=SYNC_APPLY_TIMEOUT)


def report(result: dict) -> list[str]:
    """Lines worth printing from a `syncApply` result: every rejected import, and reviews dropped.

    An Anki-only card that breaks the content rules is rejected on every run until it is fixed,
    so each rejection is named, not just counted.
    """
    lines = [f"import rejected {r['id']}: {r['error']}" for r in result.get("imports", {}).get("rejected", [])]
    skipped = result.get("reviewsSkipped") or {}
    parts = [f"{skipped[key]} {what}" for key, what in (("present", "already in the deck"), ("noCard", "of a card the deck lacks"))
             if skipped.get(key)]
    if parts:
        lines.append(f"reviews skipped: {', '.join(parts)}")
    return lines
