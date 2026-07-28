"""Tests for scripts.wiki.index — load/save index, update_entry, reindex_all."""

import json
import textwrap
from datetime import date
from pathlib import Path

from scripts.wiki.index import (
    get_wiki_key,
    load_index,
    reindex_all,
    save_index,
    update_entry,
)


class TestLoadSaveIndex:
    def test_load_missing_file(self, tmp_path: Path):
        assert load_index(tmp_path / "nonexistent.json") == {}

    def test_load_existing(self, wiki_dir: Path):
        idx_path = wiki_dir / ".wiki-index.json"
        idx_path.write_text('{"a": {"title": "A"}}\n')
        assert load_index(idx_path) == {"a": {"title": "A"}}

    def test_load_corrupt_json_returns_empty_and_backs_up(self, tmp_path: Path):
        idx_path = tmp_path / ".wiki-index.json"
        idx_path.write_text('{"trailing": "comma",}')
        result = load_index(idx_path)
        assert result == {}
        assert (tmp_path / ".wiki-index.json.bak").exists()
        assert (tmp_path / ".wiki-index.json.bak").read_text() == '{"trailing": "comma",}'

    def test_save_produces_valid_json_with_newline(self, tmp_path: Path):
        path = tmp_path / "index.json"
        save_index(path, {"key": {"title": "val"}})
        raw = path.read_text()
        assert raw.endswith("\n")
        assert json.loads(raw) == {"key": {"title": "val"}}

    def test_save_ensure_ascii_false(self, tmp_path: Path):
        path = tmp_path / "index.json"
        save_index(path, {"key": {"title": "Übersicht"}})
        raw = path.read_text()
        assert "Übersicht" in raw  # not escaped


class TestGetWikiKey:
    def test_basic(self, wiki_dir: Path):
        page = wiki_dir / "git" / "restore.md"
        assert get_wiki_key(wiki_dir, page) == "git/restore"

    def test_root_level(self, wiki_dir: Path):
        page = wiki_dir / "readme.md"
        assert get_wiki_key(wiki_dir, page) == "readme"


class TestUpdateEntry:
    def test_cuid_flashcard_ids_preserved(self, wiki_dir: Path, sample_page: Path):
        index = load_index(wiki_dir / ".wiki-index.json")
        index = update_entry(index, wiki_dir, sample_page)
        entry = index["git/test-page"]
        assert len(entry["flashcard_ids"]) == 3
        assert entry["flashcard_ids"][0] == "cmne7xz9202lx0msonsbfhp3j"
        assert all(isinstance(fid, str) for fid in entry["flashcard_ids"])

    def test_numeric_flashcard_ids(self, wiki_dir: Path):
        page_dir = wiki_dir / "js"
        page_dir.mkdir()
        page = page_dir / "closures.md"
        page.write_text(textwrap.dedent("""\
            ---
            title: "closures"
            aliases: [js closures]
            tags: [javascript]
            created: 2026-04-09
            flashcard_ids: [101, 202]
            ---

            # closures

            ## Basics

            Content.
        """))
        index = update_entry({}, wiki_dir, page)
        assert index["js/closures"]["flashcard_ids"] == ["101", "202"]

    def test_empty_flashcard_ids(self, wiki_dir: Path):
        page_dir = wiki_dir / "misc"
        page_dir.mkdir()
        page = page_dir / "no-cards.md"
        page.write_text(textwrap.dedent("""\
            ---
            title: "no cards"
            aliases: []
            tags: [misc]
            created: 2026-04-09
            flashcard_ids: []
            ---

            # no cards

            ## Overview

            No flashcards here.
        """))
        index = update_entry({}, wiki_dir, page)
        assert index["misc/no-cards"]["flashcard_ids"] == []

    def test_h2_sections_extracted(self, wiki_dir: Path, sample_page: Path):
        index = update_entry({}, wiki_dir, sample_page)
        assert index["git/test-page"]["sections"] == ["Section One", "Section Two"]

    def test_entry_fields(self, wiki_dir: Path, sample_page: Path):
        index = update_entry({}, wiki_dir, sample_page)
        entry = index["git/test-page"]
        assert entry["file"] == "git/test-page.md"
        assert entry["title"] == "test page"
        assert entry["aliases"] == ["test alias", "another alias"]
        assert entry["tags"] == ["git", "testing"]
        assert entry["created"] == "2026-04-09"
        assert entry["next_review"] == "2026-04-12"
        assert entry["review_interval"] == 3
        assert "probe_sections" not in entry
        assert "last_probed" not in entry

    def test_updated_field_set_to_today(self, wiki_dir: Path, sample_page: Path):
        index = update_entry({}, wiki_dir, sample_page)
        assert index["git/test-page"]["updated"] == date.today().isoformat()


class TestReindexAll:
    def _stale_index(self, wiki_dir: Path, page_key: str) -> None:
        save_index(
            wiki_dir / ".wiki-index.json",
            {
                page_key: {
                    "file": f"{page_key}.md",
                    "title": "test page",
                    "updated": "2026-04-09",
                    "probe_sections": ["Section One"],
                    "last_probed": ["Section One"],
                },
                "ghost/deleted-page": {"file": "ghost/deleted-page.md", "title": "Gone"},
            },
        )

    def test_drops_fields_no_longer_written(self, wiki_dir: Path, sample_page: Path):
        self._stale_index(wiki_dir, "git/test-page")
        rebuilt = reindex_all(wiki_dir)
        assert "probe_sections" not in rebuilt["git/test-page"]
        assert "last_probed" not in rebuilt["git/test-page"]

    def test_prunes_entries_for_pages_no_longer_on_disk(self, wiki_dir: Path, sample_page: Path):
        self._stale_index(wiki_dir, "git/test-page")
        assert "ghost/deleted-page" not in reindex_all(wiki_dir)

    def test_preserves_existing_updated_stamp(self, wiki_dir: Path, sample_page: Path):
        """A reindex derives from disk; it is not a write, so it must not restamp."""
        self._stale_index(wiki_dir, "git/test-page")
        assert reindex_all(wiki_dir)["git/test-page"]["updated"] == "2026-04-09"

    def test_stamps_today_for_a_page_with_no_prior_entry(self, wiki_dir: Path, sample_page: Path):
        rebuilt = reindex_all(wiki_dir)
        assert rebuilt["git/test-page"]["updated"] == date.today().isoformat()

    def test_rebuilds_content_fields_from_the_page(self, wiki_dir: Path, sample_page: Path):
        self._stale_index(wiki_dir, "git/test-page")
        entry = reindex_all(wiki_dir)["git/test-page"]
        assert entry["tags"] == ["git", "testing"]
        assert entry["next_review"] == "2026-04-12"

    def test_survives_a_previous_entry_with_no_updated_key(self, wiki_dir: Path, sample_page: Path):
        """A hand-edited or older-schema index must not crash the tool meant to fix it."""
        save_index(
            wiki_dir / ".wiki-index.json",
            {"git/test-page": {"file": "git/test-page.md", "title": "test page"}},
        )
        assert reindex_all(wiki_dir)["git/test-page"]["updated"] == date.today().isoformat()
