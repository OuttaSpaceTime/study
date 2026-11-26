"""The sync's contract with the real deck server, on an empty throwaway database.

Nothing is copied from the real deck: the app server creates the schema in an empty file
(its `prepareDatabase`), so this fails the day a Prisma migration or a change in
agentic-spaced-repetition's SDK stops accepting what anki-sync sends or returning what it reads. It
replaces the hand-written CREATE TABLE fixtures this repo's tests used to keep in step by hand.
"""

from datetime import UTC, datetime, timedelta

import pytest

from scripts.config import srs_dir
from scripts.deck.client import DeckClient, DeckError, iso

try:
    _DIR = srs_dir()
    _SKIP = None if (_DIR / "src" / "app" / "server.ts").exists() else f"no agentic-spaced-repetition app server at {_DIR}"
except RuntimeError as e:
    _SKIP = f"SRS_DIR is not configured ({e})"

pytestmark = pytest.mark.skipif(_SKIP is not None, reason=_SKIP or "")

A, B, REJECT = "ctestcard0000000000000a1", "ctestcard0000000000000b2", "ctestcard0000000000000c3"
NOW = datetime.now(UTC).replace(microsecond=0)
LAST = NOW - timedelta(days=3)
CREATED = datetime(2025, 9, 4, 15, 33, 20, tzinfo=UTC)


def schedule(**over):
    return {"due": iso(LAST + timedelta(days=10)), "stability": 10.0, "difficulty": 5.0, "reps": 3,
            "lapses": 0, "state": 2, "lastReview": iso(LAST), "interval": 10.0, **over}


def imported(card_id, front, **over):
    return {"id": card_id, "deck": "Contract Deck", "front": front, "back": "Not Modified.", "tags": ["http", "cache"],
            "exercise": None, "suspended": False, "createdAt": iso(CREATED), **schedule(), **over}


def review(card_id, at, **over):
    return {"cardId": card_id, "reviewedAt": iso(at), "rating": 3, "responseMs": 800, "state": 2, **over}


@pytest.fixture
def deck(tmp_path, monkeypatch):
    db = tmp_path / "contract.db"
    db.touch()
    monkeypatch.setenv("FLASHCARD_MASTER_DB", str(db))
    with DeckClient() as client:
        yield client


def test_an_import_a_review_a_schedule_and_a_deletion_round_trip(deck):
    assert (deck.card_records(), deck.review_records(), deck.tombstones()) == ([], [], set())

    first = deck.sync_apply(
        imports=[imported(A, "What does HTTP 304 mean?"), imported(B, "What does HTTP 404 mean?"),
                 imported(REJECT, "What is it and how is it set?", back="x" * 400)],
        reviews=[review(A, LAST), review(B, LAST)],
    )
    assert first["imports"]["imported"] == 2
    assert [r["id"] for r in first["imports"]["rejected"]] == [REJECT]
    assert first["reviews"] == 2

    (a, b) = sorted(deck.card_records(), key=lambda c: c.id)
    assert (a.id, a.deck, a.front, a.back, a.tags) == (A, "Contract Deck", "What does HTTP 304 mean?", "Not Modified.", ("http", "cache"))
    assert (a.state, a.reps, a.interval, a.stability, a.suspended) == (2, 3, 10.0, 10.0, False)
    assert a.created_at == CREATED, "an import keeps the date of its Anki note"
    assert a.last_review == LAST and a.due == LAST + timedelta(days=10)
    assert [r.card_id for r in deck.review_records(card_ids=[A])] == [A]

    new_due = NOW + timedelta(days=20)
    second = deck.sync_apply(
        schedules=[{"cardId": A, **schedule(due=iso(new_due), reps=4, interval=20.0, stability=None, difficulty=None,
                                            lastReview=iso(NOW))}],
        reviews=[review(A, NOW, rating=4), review(A, LAST), review(B, NOW)],  # the 2nd is already there; B goes
        deletions=[B],
    )
    assert second["schedules"] == 1 and second["deletions"] == 1
    assert second["reviews"] == 1
    assert second["reviewsSkipped"]["present"] == 1, "a review made twice is kept once"

    (a,) = deck.card_records()
    assert (a.id, a.reps, a.interval, a.due, a.last_review) == (A, 4, 20.0, new_due, NOW)
    assert a.stability == 10.0, "Anki without a memory state keeps the deck's"
    assert [(r.rating, r.reviewed_at) for r in deck.review_records()] == [(3, LAST), (4, NOW)]
    assert deck.tombstones() == {B}
    assert b.id not in {c.id for c in deck.card_records()}


def test_a_pulled_schedule_for_a_new_card_in_the_deck_gets_a_usable_memory_state(deck):
    deck.sync_apply(imports=[imported(A, "What does HTTP 304 mean?", state=0, reps=0, stability=0.0, difficulty=0.0,
                                      lastReview=None)])
    deck.sync_apply(schedules=[{"cardId": A, **schedule(stability=None, difficulty=None, interval=7.0)}])
    (a,) = deck.card_records()
    assert a.stability > 0, "a non-New card at stability 0 is what agentic-spaced-repetition resets to New"


def test_a_malformed_call_is_a_deck_error_not_a_hang(deck):
    with pytest.raises(DeckError, match="rating"):
        deck.sync_apply(reviews=[review(A, NOW, rating=9)])
    with pytest.raises(DeckError, match="unknown method"):
        deck.call("noSuchMethod")


def test_suspended_cards_are_left_out_on_request(deck):
    deck.sync_apply(imports=[imported(A, "What does HTTP 304 mean?"),
                             imported(B, "What does HTTP 404 mean?", suspended=True)])
    assert {c.id for c in deck.card_records()} == {A, B}
    assert {c.id for c in deck.card_records(include_suspended=False)} == {A}
