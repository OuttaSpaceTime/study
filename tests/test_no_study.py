"""Tests for scripts.wiki.no_study — the no-study-tag toggle."""

from scripts.wiki.no_study import set_no_study


class TestSetNoStudy:
    def test_adds_tag_when_excluding(self):
        meta = {"tags": ["llm", "inference"]}
        set_no_study(meta, True)
        assert meta["tags"] == ["llm", "inference", "no-study"]

    def test_excluding_is_idempotent(self):
        meta = {"tags": ["llm", "no-study"]}
        set_no_study(meta, True)
        assert meta["tags"] == ["llm", "no-study"]

    def test_removes_tag_when_including(self):
        meta = {"tags": ["llm", "no-study", "inference"]}
        set_no_study(meta, False)
        assert meta["tags"] == ["llm", "inference"]

    def test_including_is_idempotent(self):
        meta = {"tags": ["llm", "inference"]}
        set_no_study(meta, False)
        assert meta["tags"] == ["llm", "inference"]

    def test_scalar_tags_normalized_to_list(self):
        meta = {"tags": "llm"}
        set_no_study(meta, True)
        assert meta["tags"] == ["llm", "no-study"]

    def test_missing_tags_key(self):
        meta = {"title": "x"}
        set_no_study(meta, True)
        assert meta["tags"] == ["no-study"]

    def test_returns_true_when_changed(self):
        meta = {"tags": ["llm"]}
        assert set_no_study(meta, True) is True

    def test_returns_false_when_no_change(self):
        meta = {"tags": ["llm", "no-study"]}
        assert set_no_study(meta, True) is False
