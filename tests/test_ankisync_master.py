"""scripts.ankisync.master: the adapter between merge.py's dataclasses and the deck client.

What the deck does with a syncApply (the fallback memory state, the cascade, the content
rules, the review dedupe) is agentic-spaced-repetition's to test; here is only what is sent, and read.
"""

from datetime import UTC, datetime

from conftest import FakeDeck, make_card, make_review

from scripts.ankisync import master
from scripts.ankisync.merge import AnkiCard, HistoryPlan, Review, Sched, SyncPlan


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


NOTE_ID = 1_757_000_000_000  # an epoch-ms creation time, September 2025
GUID = "cmne7xoxj002z0msoiuekt37c"


def _anki(**over):
    fields = dict(note_id=NOTE_ID, card_id=2, guid=GUID, front="F", back="B", tags=("ruby",), deck="D",
                  suspended=False, sched=_sched(), exercise="")
    return AnkiCard(**{**fields, **over})


class TestReading:
    def test_a_card_record_becomes_the_sync_planners_card(self):
        deck = FakeDeck([make_card("a", tags=("design patterns", "ruby"), suspended=True, exercise='{"kind":"fill"}',
                                   inherited_from="p", interval=7.0)])
        (card,) = master.read_cards(deck)
        assert (card.id, card.deck, card.suspended, card.inherited) == ("a", "Software Engineering", True, True)
        assert card.tags == ("design_patterns", "ruby"), "a tag has no spaces in Anki"
        assert card.exercise == '{"kind":"fill"}'
        assert (card.sched.state, card.sched.interval, card.sched.stability) == (2, 7.0, 10.0)

    def test_a_plain_card_has_no_exercise_and_was_not_split(self):
        (card,) = master.read_cards(FakeDeck([make_card("a")]))
        assert (card.exercise, card.inherited) == ("", False)

    def test_reviews_and_tombstones_come_through(self):
        at = datetime(2026, 9, 1, tzinfo=UTC)
        deck = FakeDeck(reviews=[make_review("a", at, 4, response_ms=900, state=1)], tombstones=["gone"])
        assert master.read_reviews(deck) == [Review("a", at, 4, 900, 1)]
        assert master.read_tombstones(deck) == {"gone"}


class TestApplyPlan:
    def test_everything_goes_out_as_one_call(self):
        deck = FakeDeck()
        plan = SyncPlan(import_from_anki=[_anki()], local_soft_delete=[_anki(guid="cdeleted0000000000000x")],
                        pull_sched=[("c1", _sched(stability=3.5, difficulty=6.2))])
        hist = HistoryPlan(pull_reviews=[Review("c1", datetime(2026, 9, 2, 12, 0, 1, tzinfo=UTC), 3, 1200, 2)])
        master.apply_plan(deck, plan, hist)
        (call,) = deck.applied()
        assert set(call) == {"imports", "deletions", "schedules", "reviews"}
        assert call["deletions"] == ["cdeleted0000000000000x"]
        assert call["schedules"][0]["cardId"] == "c1" and call["schedules"][0]["stability"] == 3.5
        assert call["reviews"] == [{"cardId": "c1", "reviewedAt": "2026-09-02T12:00:01.000Z", "rating": 3,
                                    "responseMs": 1200, "state": 2}]

    def test_an_import_is_dated_from_its_note_id_not_from_today(self):
        """Else the deck's cards-added-today axis reads every import as intake and blocks new cards."""
        deck = FakeDeck()
        master.apply_plan(deck, SyncPlan(import_from_anki=[_anki()]), HistoryPlan())
        (imp,) = deck.applied()[0]["imports"]
        assert imp["createdAt"] == "2025-09-04T15:33:20.000Z"
        assert imp["id"] == GUID and imp["deck"] == "D" and imp["tags"] == ["ruby"]
        assert imp["state"] == 2 and imp["interval"] == 42.0
        assert imp["stability"] is None, "no FSRS memory state is sent as none; the deck fills it in"

    def test_a_code_card_arrives_with_its_exercise_and_a_plain_one_without(self):
        deck = FakeDeck()
        plan = SyncPlan(import_from_anki=[_anki(exercise='{"kind":"fill"}'), _anki(guid="cmne7xoxj002z0msoiuekt37d")])
        master.apply_plan(deck, plan, HistoryPlan())
        assert [i["exercise"] for i in deck.applied()[0]["imports"]] == ['{"kind":"fill"}', None]

    def test_a_schedule_with_no_due_date_keeps_the_decks(self):
        deck = FakeDeck()
        master.apply_plan(deck, SyncPlan(pull_sched=[("c1", _sched(due=None, last_review=None))]), HistoryPlan())
        (s,) = deck.applied()[0]["schedules"]
        assert s["due"] is None and s["lastReview"] is None


    def test_a_plan_with_nothing_for_the_deck_makes_no_call(self):
        deck = FakeDeck()
        result = master.apply_plan(deck, SyncPlan(), HistoryPlan())
        assert deck.applied() == [] and master.report(result) == []


class TestReport:
    def test_every_rejected_import_is_named_with_its_error(self):
        lines = master.report({"imports": {"imported": 1, "rejected": [
            {"id": "ca", "error": "answer too long"}, {"id": "cb", "error": "front asks two questions"}]}})
        assert lines == ["import rejected ca: answer too long", "import rejected cb: front asks two questions"]

    def test_skipped_reviews_are_said_only_when_there_are_some(self):
        assert master.report({"imports": {"imported": 0, "rejected": []},
                              "reviewsSkipped": {"present": 0, "noCard": 0}}) == []
        assert master.report({"imports": {"imported": 0, "rejected": []},
                              "reviewsSkipped": {"present": 2, "noCard": 1}}) == [
            "reviews skipped: 2 already in the deck, 1 of a card the deck lacks"]
        assert master.report({"imports": {"imported": 0, "rejected": []}}) == [], "an older server"
