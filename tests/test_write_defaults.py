"""Tests for scripts.wiki.write: _ensure_flashcard_ids and rebuild_index."""

from scripts.wiki.write import _ensure_flashcard_ids


def test_fills_flashcard_ids_when_missing():
    meta: dict = {}
    assert _ensure_flashcard_ids(meta) is True
    assert meta == {"flashcard_ids": []}


def test_leaves_existing_flashcard_ids_untouched():
    meta: dict = {"flashcard_ids": ["cmne7xz9202lx0msonsbfhp3j"]}
    assert _ensure_flashcard_ids(meta) is False
    assert meta["flashcard_ids"] == ["cmne7xz9202lx0msonsbfhp3j"]


def test_rebuild_index_prunes_deleted_pages_and_keeps_updated(tmp_path):
    import json

    from scripts.wiki.write import rebuild_index

    page = tmp_path / "a" / "one.md"
    page.parent.mkdir()
    page.write_text("---\ntitle: One\ncreated: 2026-01-01\n---\n## Part\n")
    (tmp_path / ".wiki-index.json").write_text(
        json.dumps({"a/one": {"updated": "2026-02-02"}, "a/gone": {"updated": "2026-03-03"}})
    )

    assert rebuild_index(tmp_path) == 1
    index = json.loads((tmp_path / ".wiki-index.json").read_text())
    assert list(index) == ["a/one"]
    assert index["a/one"]["updated"] == "2026-02-02"
    assert index["a/one"]["sections"] == ["Part"]
