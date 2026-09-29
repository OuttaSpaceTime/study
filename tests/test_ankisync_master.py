"""Tests for scripts.ankisync.master — memory-state fallback on Anki import.

Regression coverage for the stability=0.0 corruption bug: import_card used to
write literal 0.0 whenever Anki reported no FSRS memory_state, which is
indistinguishable from flashcard-mcp's own "corrupted card" sentinel
(scheduler.ts's sanitizeForReview resets any non-New card with stability<=0
back to a fresh New card on its next review, silently discarding its real
schedule).
"""

from datetime import UTC, datetime

from scripts.ankisync.master import _fallback_memory_state
from scripts.ankisync.merge import Sched


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
