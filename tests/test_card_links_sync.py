"""scripts/card-links-sync: a page's flashcard_ids follow a card through its splits."""

import importlib.machinery
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("card_links_sync", str(ROOT / "scripts" / "card-links-sync"))
spec = importlib.util.spec_from_loader("card_links_sync", loader)
sync = importlib.util.module_from_spec(spec)
loader.exec_module(sync)

PAGE = "---\ntitle: X\nflashcard_ids: [{}]\n---\n\nflashcard_ids: [not, this, one]\n"


def relink(ids, alive, children):
    return sync.relink(PAGE.format(ids), set(alive), children)


def test_a_split_card_is_replaced_by_its_parts():
    text, lost = relink("a, gone", ["a", "p1", "p2"], {"gone": ["p1", "p2"]})
    assert text == PAGE.format("a, p1, p2") and lost == []


def test_a_card_that_kept_its_place_gains_the_card_its_extra_moved_to():
    text, _ = relink("a", ["a", "e"], {"a": ["e"]})
    assert text == PAGE.format("a, e")


def test_a_chain_of_splits_is_followed():
    text, _ = relink("gone", ["leaf"], {"gone": ["mid"], "mid": ["leaf"]})
    assert text == PAGE.format("leaf")


def test_it_can_run_again_and_change_nothing():
    text, _ = relink("gone", ["p"], {"gone": ["p"]})
    again, _ = sync.relink(text, {"p"}, {"gone": ["p"]})
    assert again == text


def test_a_deleted_card_with_no_parts_is_reported_and_kept():
    text, lost = relink("a, nope", ["a"], {})
    assert text == PAGE.format("a, nope") and lost == ["nope"]


def test_a_page_with_no_ids_is_untouched():
    assert sync.relink("---\ntitle: X\nflashcard_ids: []\n---\n", {"a"}, {})[0] == "---\ntitle: X\nflashcard_ids: []\n---\n"


def test_the_block_form_scripts_wiki_write_leaves():
    page = "---\ntitle: X\nflashcard_ids:\n- a\n- gone\ntags: [t]\n---\n\n- gone\n"
    text, lost = sync.relink(page, {"a", "p1", "p2"}, {"gone": ["p1", "p2"]})
    assert text == "---\ntitle: X\nflashcard_ids:\n- a\n- p1\n- p2\ntags: [t]\n---\n\n- gone\n" and lost == []
    assert sync.relink(text, {"a", "p1", "p2"}, {"gone": ["p1", "p2"]})[0] == text


def test_prune_removes_what_was_deleted_and_nothing_else():
    text, lost = sync.relink(PAGE.format("a, nope"), {"a"}, {}, {"nope"})
    assert text == PAGE.format("a") and lost == ["nope"]
    page = "---\nflashcard_ids:\n- nope\n---\n"
    assert sync.relink(page, set(), {}, {"nope"})[0] == "---\nflashcard_ids: []\n---\n"


def test_prune_keeps_an_id_merely_missing_from_this_deck():
    text, lost = sync.relink(PAGE.format("a, not-synced-yet"), {"a"}, {}, {"something-else"})
    assert text == PAGE.format("a, not-synced-yet") and lost == ["not-synced-yet"]
