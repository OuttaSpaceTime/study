"""Tests for scripts.ankisync.cli reporting.

master.db owns card existence, so a card deleted on the phone is recreated by the
next sync. That undo is silent in a bare create count, which is exactly when the
developer most needs to see it.
"""

from datetime import UTC, datetime

from scripts.ankisync.cli import _summary
from scripts.ankisync.merge import HistoryPlan, MasterCard, Sched, SyncPlan

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
