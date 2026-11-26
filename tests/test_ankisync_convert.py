"""Tests for scripts.ankisync.convert — unit conversions between master.db and Anki."""

from datetime import UTC, datetime

from scripts.ankisync.convert import (
    anki_due_to_dt,
    dt_to_anki_due,
    revlog_type_to_state,
    split_tags,
    state_to_anki,
    state_to_revlog_type,
)


def _dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


class TestTags:
    def test_split_comma_separated(self):
        assert split_tags("ruby,rails") == ["ruby", "rails"]

    def test_empty_and_whitespace(self):
        assert split_tags("") == []
        assert split_tags(" ruby , rails ") == ["ruby", "rails"]

    def test_spaces_inside_tags_become_underscores(self):
        # Anki tags cannot contain spaces
        assert split_tags("design patterns,ruby") == ["design_patterns", "ruby"]


class TestStateMapping:
    # master state (ts-fsrs): 0 new, 1 learning, 2 review, 3 relearning
    # anki: ctype matches; queue 0 new, 1 learning, 2 review, -1 suspended
    def test_new(self):
        assert state_to_anki(0, suspended=False) == (0, 0)

    def test_review(self):
        assert state_to_anki(2, suspended=False) == (2, 2)

    def test_learning_and_relearning_use_learn_queue(self):
        assert state_to_anki(1, suspended=False) == (1, 1)
        assert state_to_anki(3, suspended=False) == (3, 1)

    def test_suspended_overrides_queue(self):
        assert state_to_anki(2, suspended=True) == (2, -1)


class TestDueConversion:
    # Anki review cards: due = days since collection creation day.
    # Anki learning cards: due = epoch seconds.
    COL_CRT = _dt("2026-06-01T04:00:00")  # collection creation (rollover-adjusted)

    def test_review_due_is_days_since_crt(self):
        due = _dt("2026-06-17T18:00:00")
        assert dt_to_anki_due(due, state=2, col_crt=self.COL_CRT) == 16

    def test_review_due_before_crt_clamps_to_zero(self):
        due = _dt("2026-05-20T18:00:00")
        assert dt_to_anki_due(due, state=2, col_crt=self.COL_CRT) == 0

    def test_learning_due_is_epoch_seconds(self):
        due = _dt("2026-06-08T10:00:00")
        assert dt_to_anki_due(due, state=1, col_crt=self.COL_CRT) == int(due.timestamp())

    def test_review_roundtrip_preserves_day(self):
        due = _dt("2026-06-17T18:00:00")
        anki_due = dt_to_anki_due(due, state=2, col_crt=self.COL_CRT)
        back = anki_due_to_dt(anki_due, state=2, col_crt=self.COL_CRT)
        assert back.date() == due.date()

    def test_learning_roundtrip_exact(self):
        due = _dt("2026-06-08T10:00:00")
        anki_due = dt_to_anki_due(due, state=1, col_crt=self.COL_CRT)
        assert anki_due_to_dt(anki_due, state=1, col_crt=self.COL_CRT) == due


class TestRevlogType:
    def test_reads_what_the_card_was(self):
        # learn, review, relearn, filtered; manual and rescheduled are no review state
        assert [revlog_type_to_state(t) for t in (0, 1, 2, 3, 4, 5)] == [1, 2, 3, 2, None, None]

    def test_writes_it_back_and_review_when_unknown(self):
        assert [state_to_revlog_type(s) for s in (0, 1, 2, 3, None)] == [0, 0, 1, 2, 1]
