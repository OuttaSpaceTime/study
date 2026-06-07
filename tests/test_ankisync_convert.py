"""Tests for scripts.ankisync.convert — unit conversions between master.db and Anki."""

from datetime import UTC, datetime

from scripts.ankisync.convert import (
    anki_due_to_dt,
    dt_to_anki_due,
    parse_master_dt,
    split_tags,
    state_to_anki,
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


class TestMasterDt:
    def test_parses_prisma_iso_format(self):
        dt = parse_master_dt("2026-06-17T18:00:00.000+00:00")
        assert dt == _dt("2026-06-17T18:00:00")

    def test_none_passthrough(self):
        assert parse_master_dt(None) is None

    def test_parses_legacy_epoch_ms_integers(self):
        # older Prisma versions stored DateTime as epoch milliseconds
        assert parse_master_dt(1749276473164) == _dt("2025-06-07T06:07:53.164")


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
