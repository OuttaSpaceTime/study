"""End-to-end deletion sync: cmd_sync against a fake deck and a real Anki collection.

merge.py's table is unit-tested in test_ankisync_merge.py; this covers what the
plan alone cannot see: the tag and suspend really landing on the note, the deck
being asked to delete the card, and review history staying where it belongs
while a deletion is in flight. A deletion that arrives from another
machine used to re-push the card's whole history into Anki on the way out,
because the card was still in master when history was planned but its tagged
note's reviews were not read.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from anki.collection import Collection
from conftest import FakeDeck, make_card, make_review

from scripts.ankisync import bridge, cli
from scripts.ankisync.merge import DELETED_TAG

KEEP = "cmne7xoxj002z0msoiuekt37c"
GONE = "cmne7xoz0003d0mso56mopmir"
REVIEWS_EACH = 3


@pytest.fixture
def env(tmp_path, monkeypatch):
    col_path = tmp_path / "bridge.anki2"
    # Relative to now: the fresh collection is created today, and a due day
    # before its creation clamps to day 0 (convert.dt_to_anki_due), which the
    # sync would then see as a moved due date on every run.
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(days=REVIEWS_EACH + 2)
    last = base + timedelta(days=REVIEWS_EACH - 1)

    deck = FakeDeck(
        cards=[make_card(c, front=f"question {c}?", due=last + timedelta(days=10), reps=REVIEWS_EACH, last_review=last)
               for c in (KEEP, GONE)],
        reviews=[make_review(c, base + timedelta(days=i), 3) for c in (KEEP, GONE) for i in range(REVIEWS_EACH)],
    )
    monkeypatch.setattr(cli, "DeckClient", lambda: deck)
    monkeypatch.setattr(bridge, "open_bridge", lambda: Collection(str(col_path)))
    monkeypatch.setattr(bridge, "lookup_password", lambda: None)
    monkeypatch.setattr(cli, "_load_email", lambda: None)

    env = SimpleNamespace(deck=deck, col=col_path)
    sync(env)  # push both cards and their history to Anki
    return env


def forget(deck, card_id):
    """The deck's state after a deletion: no card, no reviews, a tombstone. Set up by hand, since the
    fake does not simulate it; the cascade itself is tested in flashcard-mcp's sync-apply.test.ts."""
    deck.cards = [c for c in deck.cards if c.id != card_id]
    deck.reviews = [r for r in deck.reviews if r.card_id != card_id]
    deck._tombstones.add(card_id)
    deck.calls.clear()


def sync(env, dry_run=False):
    assert cli.cmd_sync(SimpleNamespace(local=True, dry_run=dry_run, media=False, upload=False)) == 0


def plan_line(env, capsys):
    capsys.readouterr()
    sync(env, dry_run=True)
    return capsys.readouterr().out.strip().splitlines()[-1]


def note_of(env, guid):
    col = Collection(str(env.col))
    try:
        nid = col.db.scalar("select id from notes where guid = ?", guid)
        cids = col.card_ids_of_note(nid)
        revlog = col.db.scalar(
            f"select count(*) from revlog where cid in ({','.join(map(str, cids))})"
        )
        return SimpleNamespace(
            tags=col.get_note(nid).tags,
            suspended=all(col.get_card(c).queue == -1 for c in cids),
            revlog=revlog,
        )
    finally:
        col.close()


def test_fixture_starts_converged(env, capsys):
    assert plan_line(env, capsys) == "plan: nothing to do"
    assert note_of(env, GONE).revlog == REVIEWS_EACH


class TestDeletedHere:
    """What flashcard-mcp's deleteCard leaves behind: a tombstone, no Card, no Review."""

    @pytest.fixture(autouse=True)
    def delete_here(self, env):
        forget(env.deck, GONE)

    def test_tags_and_suspends_the_note(self, env):
        sync(env)
        note = note_of(env, GONE)
        assert DELETED_TAG in note.tags
        assert note.suspended

    def test_leaves_the_notes_history_alone(self, env):
        sync(env)
        assert note_of(env, GONE).revlog == REVIEWS_EACH

    def test_converges(self, env, capsys):
        sync(env)
        assert plan_line(env, capsys) == "plan: nothing to do"


class TestDeletedElsewhere:
    """A note arriving tagged from another machine that shares the AnkiWeb collection."""

    @pytest.fixture(autouse=True)
    def delete_elsewhere(self, env):
        col = Collection(str(env.col))
        try:
            note = col.get_note(col.db.scalar("select id from notes where guid = ?", GONE))
            note.add_tag(DELETED_TAG)
            col.update_note(note)
        finally:
            col.close()

    def test_asks_the_deck_to_delete_the_card_and_nothing_else(self, env):
        """The tombstone, and the cascade of its reviews and note, are the deck's to do."""
        sync(env)
        (call,) = [c for c in env.deck.applied() if "scheduler_options" not in c]  # the options go separately
        assert call == {"imports": [], "deletions": [GONE], "schedules": [], "reviews": []}

    def test_does_not_push_the_cards_history_back_to_anki(self, env):
        sync(env)
        assert note_of(env, GONE).revlog == REVIEWS_EACH

    def test_converges(self, env, capsys):
        sync(env)
        forget(env.deck, GONE)  # what the deck does with the deletion it was asked for
        assert plan_line(env, capsys) == "plan: nothing to do"
