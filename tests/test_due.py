"""Tests for scripts.wiki.due — get_due_entries."""

from scripts.wiki.due import display_title, get_due_entries


def _make_entry(key, next_review=None, review_interval=None, title=None, tags=None):
    return {
        key: {
            "file": f"{key}.md",
            "title": title or key,
            "aliases": [],
            "tags": tags if tags is not None else ["test"],
            "sections": [],
            "flashcard_ids": [],
            "created": "2026-01-01",
            "updated": "2026-01-01",
            "next_review": next_review or "",
            "review_interval": review_interval,
        }
    }


class TestGetDueEntries:
    def test_empty_index(self):
        assert get_due_entries({}, today="2026-04-09") == []

    def test_no_next_review_excluded(self):
        index = _make_entry("a")
        assert get_due_entries(index, today="2026-04-09") == []

    def test_future_not_due(self):
        index = _make_entry("a", next_review="2026-04-15")
        assert get_due_entries(index, today="2026-04-09") == []

    def test_today_is_due(self):
        index = _make_entry("a", next_review="2026-04-09", review_interval=3.0)
        result = get_due_entries(index, today="2026-04-09")
        assert len(result) == 1
        assert result[0]["key"] == "a"
        assert result[0]["review_interval"] == 3.0

    def test_past_is_due(self):
        index = _make_entry("a", next_review="2026-04-01")
        result = get_due_entries(index, today="2026-04-09")
        assert len(result) == 1

    def test_sort_most_overdue_first(self):
        index = {}
        index.update(_make_entry("recent", next_review="2026-04-08"))
        index.update(_make_entry("old", next_review="2026-04-01"))
        index.update(_make_entry("mid", next_review="2026-04-05"))
        result = get_due_entries(index, today="2026-04-09")
        assert [r["key"] for r in result] == ["old", "mid", "recent"]

    def test_moc_tag_excluded(self):
        index = _make_entry("git/git-index", next_review="2026-04-09", tags=["moc", "git"])
        assert get_due_entries(index, today="2026-04-09") == []

    def test_non_moc_still_included(self):
        index = _make_entry("git/restore", next_review="2026-04-09", tags=["git"])
        result = get_due_entries(index, today="2026-04-09")
        assert len(result) == 1

    def test_no_study_tag_excluded(self):
        index = _make_entry("llm/kv-cache", next_review="2026-04-09", tags=["llm", "no-study"])
        assert get_due_entries(index, today="2026-04-09") == []

    def test_no_study_excluded_even_when_overdue(self):
        index = _make_entry("llm/kv-cache", next_review="2026-01-01", tags=["no-study", "llm"])
        assert get_due_entries(index, today="2026-04-09") == []

    def test_result_fields(self):
        index = _make_entry("git/restore", next_review="2026-04-09", review_interval=5.0, title="git restore")
        result = get_due_entries(index, today="2026-04-09")
        entry = result[0]
        assert entry["key"] == "git/restore"
        assert entry["file"] == "git/restore.md"
        assert entry["title"] == "git restore"
        assert entry["next_review"] == "2026-04-09"
        assert entry["review_interval"] == 5.0
        assert entry["tags"] == ["test"]
        assert entry["sections"] == []


class TestDisplayTitle:
    def test_single_folder(self):
        assert display_title("security/hsts", "HSTS") == "Security: HSTS"

    def test_nested_folder(self):
        result = display_title("rails/routing/collection-and-member-routes", "Collection and Member Routes")
        assert result == "Rails/Routing: Collection and Member Routes"

    def test_hyphenated_folder_title_cased(self):
        result = display_title("programming-languages/compilers-and-interpreters", "Compilers and Interpreters")
        assert result == "Programming Languages: Compilers and Interpreters"

    def test_acronym_override(self):
        assert display_title("sql/nullable-columns", "Nullable Columns") == "SQL: Nullable Columns"
        assert display_title("llm/kv-cache", "KV Cache") == "LLM: KV Cache"
        assert display_title("json-api/query-conventions", "Query conventions") == "JSON API: Query conventions"
        assert display_title("openapi/schema-composition", "Schema Composition") == "OpenAPI: Schema Composition"
        assert display_title("typescript/discriminated-unions", "Discriminated Unions") == "TypeScript: Discriminated Unions"
