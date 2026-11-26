"""Tests for scripts.ankisync.cli reporting.

master.db owns card existence, so a card deleted on the phone is recreated by the
next sync. That undo is silent in a bare create count, which is exactly when the
developer most needs to see it.
"""

from datetime import UTC, datetime

from scripts.ankisync.cli import _summary
from scripts.ankisync.merge import AnkiCard, HistoryPlan, MasterCard, Sched, SyncPlan

CUID = "cmne7xoxj002z0msoiuekt37c"


def _card(reps, inherited=False):
    return MasterCard(
        id=CUID,
        front="F",
        back="B",
        tags=("ruby",),
        deck="Software Engineering",
        suspended=False,
        inherited=inherited,
        sched=Sched(
            due=None,
            stability=None,
            difficulty=None,
            reps=reps,
            lapses=0,
            state=2,
            last_review=datetime(2026, 9, 4, tzinfo=UTC) if reps else None,
            interval=0.0,
        ),
    )


def _summary_for(card):
    return _summary(SyncPlan(create=[card]), HistoryPlan())


class TestReinstateReporting:
    def test_reviewed_card_missing_from_anki_is_flagged_as_reinstated(self):
        assert _summary_for(_card(reps=6)) == "create 1 (1 deleted on Anki, reinstated)"

    def test_brand_new_card_is_a_plain_create(self):
        assert _summary_for(_card(reps=0)) == "create 1"

    def test_split_carrying_inherited_reps_is_a_plain_create(self):
        assert _summary_for(_card(reps=6, inherited=True)) == "create 1"

    def test_empty_plan_still_reads_nothing_to_do(self):
        assert _summary(SyncPlan(), HistoryPlan()) == "nothing to do"


class TestImportCounts:
    """"import N" says what was imported: a card the deck refused is not."""

    def _plan(self, n):
        sched = Sched(due=None, stability=None, difficulty=None, reps=0, lapses=0, state=0, last_review=None, interval=0.0)
        return SyncPlan(import_from_anki=[
            AnkiCard(note_id=i, card_id=i, guid=f"c{i}" * 8, front="F", back="B", tags=(), deck="D", suspended=False,
                     sched=sched) for i in range(n)])

    def test_rejected_imports_are_taken_off_the_count_and_named_apart(self):
        assert _summary(self._plan(3), HistoryPlan(), rejected=1) == "import 2, import rejected 1"

    def test_all_rejected_leaves_only_the_rejection(self):
        assert _summary(self._plan(2), HistoryPlan(), rejected=2) == "import rejected 2"

    def test_none_rejected_is_as_before(self):
        assert _summary(self._plan(2), HistoryPlan()) == "import 2"
