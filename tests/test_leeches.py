from scripts.ankisync.merge import MasterCard, Sched
from scripts.leeches import LEECH_THRESHOLD, leeches


def card(
    lapses: int,
    *,
    cid: str = "c1",
    suspended: bool = False,
    stability: float | None = 10.0,
) -> MasterCard:
    return MasterCard(
        id=cid,
        front=f"front {cid}",
        back="back",
        tags=(),
        deck="Default",
        suspended=suspended,
        sched=Sched(
            due=None,
            stability=stability,
            difficulty=None,
            reps=9,
            lapses=lapses,
            state=2,
            last_review=None,
            interval=5.0,
        ),
    )


class TestThreshold:
    def test_one_below_is_excluded(self):
        assert leeches([card(LEECH_THRESHOLD - 1)]) == []

    def test_exactly_at_threshold_is_included(self):
        assert len(leeches([card(LEECH_THRESHOLD)])) == 1

    def test_above_threshold_is_included(self):
        assert len(leeches([card(LEECH_THRESHOLD + 1)])) == 1

    def test_never_lapsed_is_excluded(self):
        assert leeches([card(0)]) == []

    def test_threshold_is_overridable(self):
        assert len(leeches([card(3)], threshold=3)) == 1

    def test_empty_input(self):
        assert leeches([]) == []


class TestSuspended:
    def test_suspended_card_is_excluded_however_many_lapses(self):
        assert leeches([card(20, suspended=True)]) == []

    def test_unsuspended_card_at_the_same_count_survives(self):
        assert len(leeches([card(20)])) == 1


class TestOrdering:
    def test_highest_lapse_count_first(self):
        rows = leeches([card(5, cid="a"), card(7, cid="b"), card(6, cid="c")])
        assert [c.id for c in rows] == ["b", "c", "a"]

    def test_tie_breaks_on_lower_stability(self):
        """Equal failure history, so the weaker current memory is the more urgent card."""
        rows = leeches([card(6, cid="strong", stability=40.0), card(6, cid="weak", stability=2.0)])
        assert [c.id for c in rows] == ["weak", "strong"]

    def test_lapse_count_outranks_stability(self):
        rows = leeches([card(5, cid="fewer", stability=1.0), card(9, cid="more", stability=99.0)])
        assert [c.id for c in rows] == ["more", "fewer"]

    def test_unknown_stability_sorts_after_a_known_one(self):
        rows = leeches([card(6, cid="unknown", stability=None), card(6, cid="known", stability=30.0)])
        assert [c.id for c in rows] == ["known", "unknown"]

    def test_full_ties_keep_input_order(self):
        rows = leeches([card(6, cid="first"), card(6, cid="second")])
        assert [c.id for c in rows] == ["first", "second"]
