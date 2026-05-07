"""Tests for scripts.wiki.write._fill_defaults."""

from datetime import date, timedelta
from pathlib import Path

from scripts.wiki.write import _fill_defaults


def test_fills_review_fields_on_content_page(tmp_path: Path):
    page = tmp_path / "git" / "test-page.md"
    page.parent.mkdir(parents=True)
    page.touch()
    meta: dict = {}
    changed = _fill_defaults(page, meta)
    assert changed is True
    assert meta["review_interval"] == 3
    assert meta["next_review"] == (date.today() + timedelta(days=3)).isoformat()
    assert meta["depth"] == 1
    assert meta["flashcard_ids"] == []


def test_seeds_last_probed_from_probe_sections(tmp_path: Path):
    page = tmp_path / "git" / "test-page.md"
    page.parent.mkdir(parents=True)
    page.touch()
    meta = {"probe_sections": ["A", "B"]}
    changed = _fill_defaults(page, meta)
    assert changed is True
    assert meta["last_probed"] == ["A", "B"]


def test_does_not_overwrite_existing_last_probed(tmp_path: Path):
    page = tmp_path / "git" / "test-page.md"
    page.parent.mkdir(parents=True)
    page.touch()
    meta = {"probe_sections": ["A", "B"], "last_probed": ["A"]}
    _fill_defaults(page, meta)
    assert meta["last_probed"] == ["A"]


def test_skips_review_fields_on_index_page(tmp_path: Path):
    page = tmp_path / "git" / "git-index.md"
    page.parent.mkdir(parents=True)
    page.touch()
    meta: dict = {}
    _fill_defaults(page, meta)
    assert "review_interval" not in meta
    assert "next_review" not in meta
    assert "depth" not in meta
    assert meta["flashcard_ids"] == []


def test_seeds_last_probed_on_index_page(tmp_path: Path):
    """MOCs also get last_probed seeded from probe_sections."""
    page = tmp_path / "git" / "git-index.md"
    page.parent.mkdir(parents=True)
    page.touch()
    meta = {"probe_sections": ["Pages"]}
    _fill_defaults(page, meta)
    assert meta["last_probed"] == ["Pages"]
