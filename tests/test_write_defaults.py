"""Tests for scripts.wiki.write._ensure_flashcard_ids."""

from scripts.wiki.write import _ensure_flashcard_ids


def test_fills_flashcard_ids_when_missing():
    meta: dict = {}
    assert _ensure_flashcard_ids(meta) is True
    assert meta == {"flashcard_ids": []}


def test_leaves_existing_flashcard_ids_untouched():
    meta: dict = {"flashcard_ids": ["cmne7xz9202lx0msonsbfhp3j"]}
    assert _ensure_flashcard_ids(meta) is False
    assert meta["flashcard_ids"] == ["cmne7xz9202lx0msonsbfhp3j"]
