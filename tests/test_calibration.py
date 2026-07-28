from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from scripts.calibration import (
    MIN_REVIEWS,
    ReviewRow,
    eligible,
    is_marginal,
    rating_mix,
    render_human,
    true_retention,
    verdict,
)

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def row(rating: int, *, card: str = "c1", days_ago: float = 1.0, elapsed: float = 3.0) -> ReviewRow:
    return ReviewRow(
        card_id=card,
        rating=rating,
        reviewed_at=NOW - timedelta(days=days_ago),
        elapsed_days=elapsed,
    )


def rows_for(again: int = 0, hard: int = 0, good: int = 0, easy: int = 0) -> list[ReviewRow]:
    """One review per distinct card so nothing is deduped away."""
    out: list[ReviewRow] = []
    for rating, count in ((1, again), (2, hard), (3, good), (4, easy)):
        for i in range(count):
            out.append(row(rating, card=f"c{rating}-{i}"))
    return out


class TestEligible:
    def test_drops_intra_day_repeats(self):
        keep = row(3, card="a", elapsed=5.0)
        repeat = row(1, card="b", elapsed=0.0)
        assert eligible([keep, repeat], window_days=30, now=NOW) == [keep]

    def test_keeps_only_first_review_per_card_per_day(self):
        first = ReviewRow("a", 1, NOW - timedelta(hours=6), 4.0)
        second = ReviewRow("a", 4, NOW - timedelta(hours=2), 4.0)
        assert eligible([second, first], window_days=30, now=NOW) == [first]

    def test_same_card_on_different_days_both_count(self):
        d1 = ReviewRow("a", 3, NOW - timedelta(days=1), 4.0)
        d2 = ReviewRow("a", 3, NOW - timedelta(days=2), 4.0)
        assert len(eligible([d1, d2], window_days=30, now=NOW)) == 2

    def test_excludes_reviews_outside_window(self):
        inside = row(3, card="a", days_ago=5)
        outside = row(3, card="b", days_ago=40)
        assert eligible([inside, outside], window_days=30, now=NOW) == [inside]

    def test_calendar_day_follows_the_callers_timezone_not_utc(self):
        """A UTC+2 developer's 00:30 review is the same study day as their 15:00 one."""
        berlin = ZoneInfo("Europe/Berlin")
        now_local = datetime(2026, 7, 28, 20, 0, tzinfo=berlin)
        early = ReviewRow("a", 1, datetime(2026, 7, 27, 22, 30, tzinfo=UTC), 4.0)
        later = ReviewRow("a", 3, datetime(2026, 7, 28, 13, 0, tzinfo=UTC), 4.0)
        assert eligible([early, later], window_days=30, now=now_local) == [early]

    def test_utc_day_boundary_would_have_split_them(self):
        """Same two reviews under a UTC clock are two days — the bug this guards against."""
        early = ReviewRow("a", 1, datetime(2026, 7, 27, 22, 30, tzinfo=UTC), 4.0)
        later = ReviewRow("a", 3, datetime(2026, 7, 28, 13, 0, tzinfo=UTC), 4.0)
        now_utc = datetime(2026, 7, 28, 20, 0, tzinfo=UTC)
        assert len(eligible([early, later], window_days=30, now=now_utc)) == 2


class TestRetention:
    def test_pass_is_rating_three_or_better(self):
        assert true_retention(rows_for(again=1, hard=1, good=1, easy=1)) == pytest.approx(0.5)

    def test_none_when_no_rows(self):
        assert true_retention([]) is None

    def test_rating_mix_counts_each_bucket(self):
        assert rating_mix(rows_for(again=2, hard=1, good=5, easy=2)) == {
            "again": 2,
            "hard": 1,
            "good": 5,
            "easy": 2,
        }


class TestVerdict:
    def test_low_signal_below_minimum_reviews(self):
        token, reasons = verdict(rows_for(good=MIN_REVIEWS - 1))
        assert token == "low-signal"
        assert any("reviews" in r for r in reasons)

    def test_low_signal_when_good_share_dominates(self):
        token, reasons = verdict(rows_for(again=5, good=45))
        assert token == "low-signal"
        assert any("discrimination" in r for r in reasons)

    def test_over_difficult_below_eighty(self):
        token, _ = verdict(rows_for(again=15, good=35))
        assert token == "over-difficult"

    def test_calibrated_inside_band(self):
        token, _ = verdict(rows_for(again=4, hard=3, good=35, easy=8))
        assert token == "calibrated"

    def test_under_difficult_above_ninety(self):
        token, _ = verdict(rows_for(again=2, good=38, easy=10))
        assert token == "under-difficult"

    def test_marginal_just_below_the_band(self):
        """79% is over-difficult but within noise of the 80% floor."""
        assert is_marginal("over-difficult", 0.79) is True

    def test_marginal_just_above_the_band(self):
        assert is_marginal("under-difficult", 0.91) is True

    def test_not_marginal_well_inside_band(self):
        assert is_marginal("calibrated", 0.86) is False

    def test_not_marginal_well_below_band(self):
        assert is_marginal("over-difficult", 0.70) is False

    def test_marginal_is_false_without_retention(self):
        assert is_marginal("low-signal", None) is False

    def test_discrimination_gate_precedes_band_check(self):
        """A dominant-Good mix lands in the calibrated band but must not be trusted."""
        rows = rows_for(again=5, good=45)
        assert true_retention(rows) == pytest.approx(0.9)
        assert verdict(rows)[0] == "low-signal"


class TestVerdictBoundaries:
    """The band edges are inclusive of CALIBRATED; a < / <= slip must fail a test."""

    def test_exactly_eighty_percent_is_calibrated(self):
        rows = rows_for(again=10, good=40)
        assert true_retention(rows) == pytest.approx(0.80)
        assert verdict(rows)[0] == "calibrated"

    def test_exactly_ninety_percent_is_calibrated(self):
        rows = rows_for(hard=5, good=40, easy=5)
        assert true_retention(rows) == pytest.approx(0.90)
        assert verdict(rows)[0] == "calibrated"


class TestMarginalIsSuppressedForLowSignal:
    """Marginality is meaningless when the verdict says retention isn't trustworthy."""

    def test_low_signal_output_is_never_also_marginal(self):
        rows = rows_for(again=5, good=45)
        token, reasons = verdict(rows)
        assert token == "low-signal"
        assert true_retention(rows) == pytest.approx(0.90)
        marginal = is_marginal(token, true_retention(rows))
        assert marginal is False
        rendered = render_human(token, reasons, rows, 30, marginal)
        assert "MARGINAL" not in rendered
        assert "soften levers" not in rendered

    def test_marginal_still_shows_for_a_retention_backed_verdict(self):
        rows = rows_for(again=10, hard=1, good=33, easy=6)
        token, reasons = verdict(rows)
        assert token == "over-difficult"
        assert true_retention(rows) == pytest.approx(0.78)
        marginal = is_marginal(token, true_retention(rows))
        assert marginal is True
        assert "MARGINAL" in render_human(token, reasons, rows, 30, marginal)


class TestMarginBoundaryIsExact:
    """A retention exactly MARGIN from an edge must count; float error must not exclude it."""

    def test_exactly_margin_below_the_floor(self):
        assert is_marginal("over-difficult", 0.78) is True

    def test_exactly_margin_above_the_ceiling(self):
        assert is_marginal("under-difficult", 0.92) is True

    def test_a_hair_further_out_is_not_marginal(self):
        assert is_marginal("over-difficult", 0.7799) is False
