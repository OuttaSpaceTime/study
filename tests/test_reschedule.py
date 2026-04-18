"""Tests for scripts.wiki.reschedule — compute_schedule and reschedule_page."""

import textwrap
from datetime import date

import pytest

from scripts.wiki.reschedule import compute_schedule, reschedule_page


class TestComputeSchedule:
    """Test the scheduling algorithm for each rating."""

    def test_again_resets_to_1(self):
        result = compute_schedule(current_interval=20, rating=1, today="2026-04-14")
        assert result == {"review_interval": 1, "next_review": "2026-04-15"}

    def test_again_from_small_interval(self):
        result = compute_schedule(current_interval=3, rating=1, today="2026-04-14")
        assert result == {"review_interval": 1, "next_review": "2026-04-15"}

    def test_hard_minimum_3(self):
        # 1 * 1.2 = 1.2 -> rounds to 1, but min is 3
        result = compute_schedule(current_interval=1, rating=2, today="2026-04-14")
        assert result["review_interval"] == 3
        assert result["next_review"] == "2026-04-17"

    def test_hard_scales(self):
        # 5 * 1.2 = 6
        result = compute_schedule(current_interval=5, rating=2, today="2026-04-14")
        assert result["review_interval"] == 6
        assert result["next_review"] == "2026-04-20"

    def test_good_scales(self):
        # 3 * 2.5 = 7.5 -> 8
        result = compute_schedule(current_interval=3, rating=3, today="2026-04-14")
        assert result["review_interval"] == 8
        assert result["next_review"] == "2026-04-22"

    def test_easy_scales(self):
        # 3 * 4 = 12
        result = compute_schedule(current_interval=3, rating=4, today="2026-04-14")
        assert result["review_interval"] == 12
        assert result["next_review"] == "2026-04-26"

    def test_good_progression(self):
        """Good streak: 3 -> 8 -> 20 -> 50 -> 125."""
        intervals = [3]
        for _ in range(4):
            result = compute_schedule(intervals[-1], 3, "2026-01-01")
            intervals.append(result["review_interval"])
        assert intervals == [3, 8, 20, 50, 125]

    def test_easy_progression(self):
        """Easy streak: 3 -> 12 -> 48 -> 192."""
        intervals = [3]
        for _ in range(3):
            result = compute_schedule(intervals[-1], 4, "2026-01-01")
            intervals.append(result["review_interval"])
        assert intervals == [3, 12, 48, 192]

    def test_hard_progression(self):
        """Hard streak: 3 -> 4 -> 5 -> 6 -> 7."""
        intervals = [3]
        for _ in range(4):
            result = compute_schedule(intervals[-1], 2, "2026-01-01")
            intervals.append(result["review_interval"])
        assert intervals == [3, 4, 5, 6, 7]

    def test_invalid_rating_raises(self):
        with pytest.raises(ValueError, match="rating must be 1-4"):
            compute_schedule(3, 0, "2026-04-14")
        with pytest.raises(ValueError, match="rating must be 1-4"):
            compute_schedule(3, 5, "2026-04-14")

    def test_defaults_today(self):
        result = compute_schedule(3, 1)
        expected_next = (date.today().toordinal() + 1)
        actual_next = date.fromisoformat(result["next_review"]).toordinal()
        assert actual_next == expected_next


class TestReschedulePage:
    """Test frontmatter rewriting on actual wiki files."""

    def test_updates_frontmatter(self, wiki_dir, sample_page):
        result = reschedule_page(sample_page, rating=3, today="2026-04-14")

        # sample_page has review_interval: 3, so Good -> 8
        assert result["review_interval"] == 8
        assert result["next_review"] == "2026-04-22"

        # Verify the file was rewritten
        content = sample_page.read_text()
        assert "review_interval: 8" in content
        assert "next_review: '2026-04-22'" in content or "next_review: 2026-04-22" in content

    def test_preserves_body(self, wiki_dir, sample_page):
        original_body = sample_page.read_text().split("---\n", 2)[2]
        reschedule_page(sample_page, rating=4, today="2026-04-14")
        new_body = sample_page.read_text().split("---\n", 2)[2]
        assert new_body == original_body

    def test_preserves_other_frontmatter(self, wiki_dir, sample_page):
        reschedule_page(sample_page, rating=3, today="2026-04-14")
        content = sample_page.read_text()
        assert 'title: "test page"' in content or "title: test page" in content
        assert "source_skill: study-walkthrough" in content

    def test_missing_interval_defaults_to_3(self, wiki_dir):
        page = wiki_dir / "no-interval.md"
        page.write_text(textwrap.dedent("""\
            ---
            title: "no interval"
            aliases: []
            tags: [test]
            created: 2026-04-14
            updated: 2026-04-14
            source_skill: test
            ---

            # No interval

            Content.
        """))
        result = reschedule_page(page, rating=3, today="2026-04-14")
        # Default interval 3, Good -> 8
        assert result["review_interval"] == 8

    def test_no_frontmatter_raises(self, wiki_dir):
        page = wiki_dir / "bare.md"
        page.write_text("# No frontmatter\n\nJust content.\n")
        with pytest.raises(ValueError, match="No frontmatter"):
            reschedule_page(page, rating=3)
