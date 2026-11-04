"""Tests for scripts.ankisync.master — memory-state fallback on Anki import.

Regression coverage for the stability=0.0 corruption bug: import_card used to
write literal 0.0 whenever Anki reported no FSRS memory_state, which is
indistinguishable from flashcard-mcp's own "corrupted card" sentinel
(scheduler.ts's sanitizeForReview resets any non-New card with stability<=0
back to a fresh New card on its next review, silently discarding its real
schedule).
"""

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime

from scripts.ankisync.master import _fallback_memory_state, import_card
from scripts.ankisync.merge import AnkiCard, Sched


def _sched(**overrides):
    defaults = dict(
        due=datetime(2026, 10, 1, tzinfo=UTC),
        stability=None,
        difficulty=None,
        reps=5,
        lapses=1,
        state=2,  # Review
        last_review=datetime(2026, 9, 1, tzinfo=UTC),
        interval=42.0,
    )
    defaults.update(overrides)
    return Sched(**defaults)


class TestFallbackMemoryState:
    def test_real_memory_state_passes_through_unchanged(self):
        sched = _sched(stability=3.5, difficulty=6.2)
        assert _fallback_memory_state(sched) == (3.5, 6.2)

    def test_missing_memory_state_on_review_card_falls_back_to_interval(self):
        sched = _sched(stability=None, difficulty=None, state=2, interval=42.0)
        stability, difficulty = _fallback_memory_state(sched)
        assert stability == 42.0
        assert difficulty == 5.0

    def test_missing_memory_state_never_produces_the_corruption_sentinel(self):
        # A short interval must still floor above 0 — 0.0 is what
        # sanitizeForReview treats as corrupted on any non-New card.
        sched = _sched(stability=None, difficulty=None, state=3, interval=0.0)
        stability, _difficulty = _fallback_memory_state(sched)
        assert stability > 0.0

    def test_missing_memory_state_on_new_card_stays_zero(self):
        # State New genuinely has no memory yet — 0.0 is correct here, not corruption.
        sched = _sched(stability=None, difficulty=None, state=0, interval=0.0)
        assert _fallback_memory_state(sched) == (0.0, 0.0)

    def test_partial_memory_state_still_falls_back(self):
        # Anki only ever reports both fields together in practice, but guard
        # against a stability/difficulty pair that's only half-populated.
        sched = _sched(stability=3.5, difficulty=None, state=2, interval=10.0)
        stability, difficulty = _fallback_memory_state(sched)
        assert stability == 10.0
        assert difficulty == 5.0


class TestImportKeepsTheExercise:
    """A code card first seen on another machine has to arrive able to run."""

    def test_the_exercise_comes_with_the_import(self):
        con = sqlite3.connect(":memory:")
        con.executescript(
            """CREATE TABLE Deck (id TEXT PRIMARY KEY, name TEXT, createdAt TEXT);
               CREATE TABLE Card (id TEXT PRIMARY KEY, deckId TEXT, front TEXT, back TEXT, tags TEXT,
                 due TEXT, stability REAL, difficulty REAL, reps INT, lapses INT, state INT, lastReview TEXT,
                 interval REAL, suspended INT, createdAt TEXT, updatedAt TEXT, exercise TEXT);"""
        )
        card = AnkiCard(note_id=1_757_000_000_000, card_id=2, guid="cmne7xoxj002z0msoiuekt37c", front="F", back="B",
                        tags=(), deck="D", suspended=False, sched=_sched(stability=1.0, difficulty=5.0),
                        exercise='{"kind":"fill"}')
        import_card(con, card)
        import_card(con, replace(card, guid="cmne7xoxj002z0msoiuekt37d", exercise=""))
        assert [r[0] for r in con.execute("SELECT exercise FROM Card ORDER BY id")] == ['{"kind":"fill"}', None]
