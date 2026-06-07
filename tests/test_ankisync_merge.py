"""Tests for scripts.ankisync.merge — stateless sync planning (pure decision logic).

Direction contract:
- master.db owns card existence and content (one-way push to Anki, master wins).
- Scheduling flows both ways: the side with the newer last review wins wholesale.
- Review history is append-only: union by (card, timestamp), nothing overwritten.
- Anki-only notes (non-CUID guid) are reported, never imported into master.
- No sync bookkeeping: every decision derives from current state of both sides.
"""

from datetime import UTC, datetime

from scripts.ankisync.merge import (
    AnkiCard,
    MasterCard,
    Review,
    Sched,
    is_cuid,
    plan_history,
    plan_sync,
)


def _dt(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


CUID = "cmne7xoxj002z0msoiuekt37c"
CUID2 = "cmne7xoz0003d0mso56mopmir"


def _sched(last_review=None, reps=0, state=0, due=None, **kw):
    defaults = dict(stability=None, difficulty=None, lapses=0, interval=0.0)
    defaults.update(kw)
    return Sched(
        due=_dt(due) if due else None,
        last_review=_dt(last_review) if last_review else None,
        reps=reps,
        state=state,
        **defaults,
    )


def _master(id=CUID, front="F", back="B", tags=("ruby",), deck="Software Engineering",
            suspended=False, sched=None):
    return MasterCard(id=id, front=front, back=back, tags=tuple(tags), deck=deck,
                      suspended=suspended, sched=sched or _sched())


def _anki(note_id=100, card_id=200, guid=CUID, front="F", back="B", tags=("ruby",),
          deck="Software Engineering", suspended=False, sched=None):
    return AnkiCard(note_id=note_id, card_id=card_id, guid=guid, front=front, back=back,
                    tags=tuple(tags), deck=deck, suspended=suspended, sched=sched or _sched())


class TestCuidShape:
    def test_real_cuids_match(self):
        assert is_cuid(CUID) and is_cuid(CUID2)

    def test_anki_native_guids_do_not_match(self):
        # Anki generates short base91 guids with mixed case / symbols
        for guid in ("f$kz$Y9Z*m", "Ab3(x~Q&zP", "short"):
            assert not is_cuid(guid)


class TestPlanExistence:
    def test_master_card_missing_in_anki_is_created(self):
        plan = plan_sync([_master()], [])
        assert [c.id for c in plan.create] == [CUID]
        assert not plan.update_content and not plan.delete_notes

    def test_cuid_note_without_master_card_is_deleted(self):
        plan = plan_sync([], [_anki(guid=CUID)])
        assert plan.delete_notes == [100]

    def test_foreign_guid_note_is_reported_never_deleted(self):
        plan = plan_sync([], [_anki(note_id=999, guid="f$kz$Y9Z*m")])
        assert plan.unknown_anki == [999]
        assert not plan.delete_notes and not plan.pull_sched


class TestPlanContent:
    def test_identical_content_is_untouched(self):
        plan = plan_sync([_master()], [_anki()])
        assert not plan.create and not plan.update_content

    def test_any_field_difference_pushes_master_version(self):
        for variant in (_anki(back="B-edited"), _anki(tags=("ruby", "rails")),
                        _anki(deck="Other"), _anki(front="F-edited")):
            plan = plan_sync([_master()], [variant])
            assert plan.update_content == [(_master(), 100)], variant

    def test_tag_order_is_not_a_difference(self):
        # Anki stores tags sorted; order must not trigger endless re-pushes
        plan = plan_sync([_master(tags=("Security", "CSP"))], [_anki(tags=("CSP", "Security"))])
        assert not plan.update_content

    def test_tag_case_is_not_a_difference(self):
        # Anki tags are case-insensitive; first-seen casing wins and sticks
        plan = plan_sync([_master(tags=("xss",))], [_anki(tags=("XSS",))])
        assert not plan.update_content

    def test_master_wins_regardless_of_which_side_changed(self):
        # stateless: an Anki-side edit is indistinguishable and gets overwritten
        card = _master(back="master version")
        plan = plan_sync([card], [_anki(back="anki edit")])
        assert plan.update_content == [(card, 100)]


class TestPlanScheduling:
    def test_our_newer_review_pushes_sched(self):
        card = _master(sched=_sched(last_review="2026-06-07T09:00", reps=3, state=2))
        anki = _anki(sched=_sched(last_review="2026-06-01T09:00", reps=2, state=2))
        plan = plan_sync([card], [anki])
        assert plan.push_sched == [(card, 200)]
        assert not plan.pull_sched

    def test_their_newer_review_pulls_sched(self):
        card = _master(sched=_sched(last_review="2026-06-01T09:00", reps=2, state=2))
        anki = _anki(sched=_sched(last_review="2026-06-07T09:00", reps=3, state=2))
        plan = plan_sync([card], [anki])
        assert plan.pull_sched == [(CUID, anki.sched)]
        assert not plan.push_sched

    def test_never_reviewed_on_either_side_does_nothing(self):
        plan = plan_sync([_master()], [_anki()])
        assert not plan.push_sched and not plan.pull_sched

    def test_our_review_their_none_pushes(self):
        card = _master(sched=_sched(last_review="2026-06-07T09:00", reps=1, state=2))
        plan = plan_sync([card], [_anki()])
        assert plan.push_sched == [(card, 200)]

    def test_equal_timestamps_do_nothing(self):
        s = _sched(last_review="2026-06-07T09:00", reps=1, state=2)
        plan = plan_sync([_master(sched=s)], [_anki(sched=s)])
        assert not plan.push_sched and not plan.pull_sched

    def test_subsecond_difference_is_not_a_newer_review(self):
        # Anki stores last_review_time in whole seconds; master keeps milliseconds
        ours = _sched(last_review="2026-06-07T09:00:53.164", reps=1, state=2)
        theirs = _sched(last_review="2026-06-07T09:00:53.000", reps=1, state=2)
        plan = plan_sync([_master(sched=ours)], [_anki(sched=theirs)])
        assert not plan.push_sched and not plan.pull_sched


class TestPlanSuspension:
    def test_master_suspension_wins(self):
        card = _master(suspended=True)
        plan = plan_sync([card], [_anki()])
        assert plan.push_suspend == [(card, 200)]

    def test_matching_suspension_untouched(self):
        plan = plan_sync([_master(suspended=True)], [_anki(suspended=True)])
        assert not plan.push_suspend


class TestPlanHistory:
    """Union by (card_id, reviewed_at) — append-only, nothing overwritten."""

    def _rev(self, ts, rating=3, card_id=CUID):
        return Review(card_id=card_id, reviewed_at=_dt(ts), rating=rating, response_ms=None)

    def test_identical_history_does_nothing(self):
        ours = [self._rev("2026-06-01T09:00")]
        theirs = [self._rev("2026-06-01T09:00")]
        plan = plan_history(ours, theirs)
        assert not plan.pull_reviews and not plan.push_reviews

    def test_anki_only_review_is_pulled(self):
        theirs = [self._rev("2026-06-07T09:00", rating=2)]
        plan = plan_history([], theirs)
        assert plan.pull_reviews == theirs

    def test_master_only_review_is_pushed(self):
        ours = [self._rev("2026-06-07T09:00")]
        plan = plan_history(ours, [])
        assert plan.push_reviews == ours

    def test_union_is_per_card(self):
        ours = [self._rev("2026-06-01T09:00", card_id=CUID)]
        theirs = [self._rev("2026-06-01T09:00", card_id=CUID2)]
        plan = plan_history(ours, theirs)
        assert plan.push_reviews == ours
        assert plan.pull_reviews == theirs

    def test_subsecond_drift_is_the_same_review(self):
        # Anki bumps revlog ids by +1ms on collision; union key rounds to seconds
        ours = [self._rev("2026-06-07T09:00:00.000")]
        theirs = [self._rev("2026-06-07T09:00:00.001")]
        plan = plan_history(ours, theirs)
        assert not plan.pull_reviews and not plan.push_reviews

    def test_both_sides_reviewed_between_syncs_keeps_both_rows(self):
        # the scheduling layer picks one winner, but history keeps everything
        ours = [self._rev("2026-06-07T09:00")]
        theirs = [self._rev("2026-06-06T18:00")]
        plan = plan_history(ours, theirs)
        assert plan.push_reviews == ours
        assert plan.pull_reviews == theirs
