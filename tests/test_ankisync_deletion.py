"""End-to-end deletion sync: cmd_sync against a real master.db and Anki collection.

merge.py's table is unit-tested in test_ankisync_merge.py; this covers what the
plan alone cannot see: the tag and suspend really landing on the note, the Card
row and its history really leaving master, and review history staying where it
belongs while a deletion is in flight. A deletion that arrives from another
machine used to re-push the card's whole history into Anki on the way out,
because the card was still in master when history was planned but its tagged
note's reviews were not read.
"""

import sqlite3
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from anki.collection import Collection

from scripts.ankisync import bridge, cli
from scripts.ankisync.convert import format_master_dt
from scripts.ankisync.merge import DELETED_TAG

KEEP = "cmne7xoxj002z0msoiuekt37c"
GONE = "cmne7xoz0003d0mso56mopmir"
REVIEWS_EACH = 3

SCHEMA = """
CREATE TABLE Deck (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
                   createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE Card (
    id TEXT PRIMARY KEY, deckId TEXT NOT NULL REFERENCES Deck(id) ON DELETE CASCADE,
    front TEXT NOT NULL, back TEXT NOT NULL, tags TEXT NOT NULL DEFAULT '',
    inheritedFrom TEXT, due DATETIME NOT NULL, stability REAL NOT NULL DEFAULT 0,
    difficulty REAL NOT NULL DEFAULT 0, reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0, state INTEGER NOT NULL DEFAULT 0,
    lastReview DATETIME, interval REAL NOT NULL DEFAULT 0,
    suspended BOOLEAN NOT NULL DEFAULT false,
    createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, updatedAt DATETIME NOT NULL);
CREATE TABLE Review (
    id TEXT PRIMARY KEY, cardId TEXT NOT NULL REFERENCES Card(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL, responseMs INTEGER, stability REAL NOT NULL,
    difficulty REAL NOT NULL, elapsedDays REAL NOT NULL, reviewedAt DATETIME NOT NULL);
CREATE TABLE DeletedCard (cardId TEXT PRIMARY KEY, deletedAt DATETIME NOT NULL);
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    master_path = tmp_path / "master.db"
    col_path = tmp_path / "bridge.anki2"
    base = datetime(2026, 9, 1, tzinfo=UTC)

    with sqlite3.connect(master_path) as con:
        con.executescript(SCHEMA)
        con.execute("INSERT INTO Deck (id, name) VALUES ('d1', 'Software Engineering')")
        for card_id in (KEEP, GONE):
            last = base + timedelta(days=REVIEWS_EACH - 1)
            con.execute(
                """INSERT INTO Card (id, deckId, front, back, due, stability, difficulty,
                                     reps, state, lastReview, interval, updatedAt)
                   VALUES (?, 'd1', ?, 'an answer', ?, 10.0, 5.0, ?, 2, ?, 10.0, ?)""",
                (
                    card_id,
                    f"question {card_id}?",
                    format_master_dt(last + timedelta(days=10)),
                    REVIEWS_EACH,
                    format_master_dt(last),
                    format_master_dt(last),
                ),
            )
            for i in range(REVIEWS_EACH):
                con.execute(
                    """INSERT INTO Review (id, cardId, rating, stability, difficulty,
                                           elapsedDays, reviewedAt)
                       VALUES (?, ?, 3, 10.0, 5.0, 1.0, ?)""",
                    (f"r{i}{card_id}", card_id, format_master_dt(base + timedelta(days=i))),
                )

    monkeypatch.setenv("FLASHCARD_MASTER_DB", str(master_path))
    monkeypatch.setattr(bridge, "open_bridge", lambda: Collection(str(col_path)))
    monkeypatch.setattr(bridge, "lookup_password", lambda: None)
    monkeypatch.setattr(cli, "_load_email", lambda: None)

    env = SimpleNamespace(master=master_path, col=col_path)
    sync(env)  # push both cards and their history to Anki
    return env


def sync(env, dry_run=False):
    assert cli.cmd_sync(SimpleNamespace(local=True, dry_run=dry_run, media=False, upload=False)) == 0


def plan_line(env, capsys):
    capsys.readouterr()
    sync(env, dry_run=True)
    return capsys.readouterr().out.strip().splitlines()[-1]


def master_rows(env, sql, *params):
    with sqlite3.connect(env.master) as con:
        return con.execute(sql, params).fetchall()


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
        with sqlite3.connect(env.master) as con:
            con.execute(
                "INSERT INTO DeletedCard VALUES (?, ?)", (GONE, format_master_dt(datetime.now(UTC)))
            )
            con.execute("DELETE FROM Review WHERE cardId = ?", (GONE,))
            con.execute("DELETE FROM Card WHERE id = ?", (GONE,))

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

    def test_removes_the_card_and_records_a_tombstone(self, env):
        sync(env)
        assert master_rows(env, "SELECT id FROM Card WHERE id = ?", GONE) == []
        assert master_rows(env, "SELECT cardId FROM DeletedCard") == [(GONE,)]

    def test_removes_the_cards_reviews_like_a_local_delete(self, env):
        sync(env)
        assert master_rows(env, "SELECT id FROM Review WHERE cardId = ?", GONE) == []
        assert len(master_rows(env, "SELECT id FROM Review WHERE cardId = ?", KEEP)) == (
            REVIEWS_EACH
        )

    def test_does_not_push_the_cards_history_back_to_anki(self, env):
        sync(env)
        assert note_of(env, GONE).revlog == REVIEWS_EACH

    def test_converges(self, env, capsys):
        sync(env)
        assert plan_line(env, capsys) == "plan: nothing to do"
