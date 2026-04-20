"""Tests for scripts.wiki.index — load/save index, update_entry."""

import json
import textwrap
from pathlib import Path

from scripts.wiki.index import get_wiki_key, load_index, save_index, update_entry


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

    def test_category_round_trips(self, wiki_dir: Path, sample_page: Path):
        index = update_entry({}, wiki_dir, sample_page)
        assert index["git/test-page"]["category"] == "work"

    def test_updated_field_set_to_today(self, wiki_dir: Path, sample_page: Path):
        from datetime import date

        index = update_entry({}, wiki_dir, sample_page)
        assert index["git/test-page"]["updated"] == date.today().isoformat()
