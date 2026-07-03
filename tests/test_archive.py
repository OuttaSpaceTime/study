"""Tests for scripts.wiki.archive — the archived-tag toggle."""

from scripts.wiki.archive import set_archived


class TestSetArchived:
    def test_adds_tag_when_archiving(self):
        meta = {"tags": ["llm", "inference"]}
        set_archived(meta, True)
        assert meta["tags"] == ["llm", "inference", "archived"]

    def test_archiving_is_idempotent(self):
        meta = {"tags": ["llm", "archived"]}
        set_archived(meta, True)
        assert meta["tags"] == ["llm", "archived"]

    def test_removes_tag_when_unarchiving(self):
        meta = {"tags": ["llm", "archived", "inference"]}
        set_archived(meta, False)
        assert meta["tags"] == ["llm", "inference"]

    def test_unarchiving_is_idempotent(self):
        meta = {"tags": ["llm", "inference"]}
        set_archived(meta, False)
        assert meta["tags"] == ["llm", "inference"]

    def test_scalar_tags_normalized_to_list(self):
        meta = {"tags": "llm"}
        set_archived(meta, True)
        assert meta["tags"] == ["llm", "archived"]

    def test_missing_tags_key(self):
        meta = {"title": "x"}
        set_archived(meta, True)
        assert meta["tags"] == ["archived"]

    def test_returns_true_when_changed(self):
        meta = {"tags": ["llm"]}
        assert set_archived(meta, True) is True

    def test_returns_false_when_no_change(self):
        meta = {"tags": ["llm", "archived"]}
        assert set_archived(meta, True) is False
