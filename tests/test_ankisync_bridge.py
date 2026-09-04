"""Tests for scripts.ankisync.bridge — the Anki-side reads that feed sync planning.

An AnkiWeb sync-down delivers a remote review as a revlog row but leaves the
card's last_review_time unset, so the revlog is the only trustworthy record of
when Anki last saw the card. It is also the only one we never overwrite:
write_sched rewrites last_review_time on every push.
"""

from anki.collection import Collection

from scripts.ankisync import bridge

CUID = "cmne7xoxj002z0msoiuekt37c"
REVIEWED_MS = 1_757_000_000_000


def _collection(tmp_path) -> Collection:
    return Collection(str(tmp_path / "test.anki2"))


def _add_card(col, *, reps=3, last_review_time=0):
    note = col.new_note(col.models[bridge.NOTETYPE])
    note.guid = CUID
    note.fields[0] = "F"
    note.fields[1] = "B"
    col.add_note(note, col.decks.id_for_name("Default"))
    cid = col.card_ids_of_note(note.id)[0]
    card = col.get_card(cid)
    card.type, card.queue, card.reps = 2, 2, reps
    card.last_review_time = last_review_time
    col.update_card(card)
    return cid


def _add_revlog(col, cid, ms=REVIEWED_MS, ease=3):
    col.db.execute(
        """insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
           values (?, ?, -1, ?, 0, 0, 0, 0, 1)""",
        ms,
        cid,
        ease,
    )


class TestAnkiLastReview:
    def test_derives_from_revlog_when_card_field_unset(self, tmp_path):
        col = _collection(tmp_path)
        try:
            cid = _add_card(col, last_review_time=0)
            _add_revlog(col, cid)
            (card,) = bridge.read_anki_cards(col)
            assert card.sched.last_review is not None
            assert int(card.sched.last_review.timestamp()) == REVIEWED_MS // 1000
        finally:
            col.close()

    def test_prefers_revlog_over_a_stale_card_field(self, tmp_path):
        col = _collection(tmp_path)
        try:
            cid = _add_card(col, last_review_time=REVIEWED_MS // 1000 - 90 * 86400)
            _add_revlog(col, cid)
            (card,) = bridge.read_anki_cards(col)
            assert int(card.sched.last_review.timestamp()) == REVIEWED_MS // 1000
        finally:
            col.close()

    def test_none_when_never_reviewed(self, tmp_path):
        col = _collection(tmp_path)
        try:
            _add_card(col, reps=0, last_review_time=0)
            (card,) = bridge.read_anki_cards(col)
            assert card.sched.last_review is None
        finally:
            col.close()

    def test_falls_back_to_card_field_when_no_revlog(self, tmp_path):
        # Cards can carry scheduling with no reviews of their own (an inheritFrom
        # split copies the parent's block). With no revlog on either side there is
        # nothing fresher to learn, so the field stands and the sides tie.
        col = _collection(tmp_path)
        try:
            ts = REVIEWED_MS // 1000
            _add_card(col, last_review_time=ts)
            (card,) = bridge.read_anki_cards(col)
            assert int(card.sched.last_review.timestamp()) == ts
        finally:
            col.close()

    def test_ignores_non_review_revlog_entries(self, tmp_path):
        col = _collection(tmp_path)
        try:
            cid = _add_card(col, last_review_time=0)
            _add_revlog(col, cid, ms=REVIEWED_MS)
            _add_revlog(col, cid, ms=REVIEWED_MS + 86_400_000, ease=0)  # set-due-date
            (card,) = bridge.read_anki_cards(col)
            assert int(card.sched.last_review.timestamp()) == REVIEWED_MS // 1000
        finally:
            col.close()
