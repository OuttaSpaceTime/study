"""Tests for scripts.ankisync.bridge — the Anki-side reads that feed sync planning.

An AnkiWeb sync-down delivers a remote review as a revlog row but leaves the
card's last_review_time unset, so the revlog is the only trustworthy record of
when Anki last saw the card. It is also the only one we never overwrite:
write_sched rewrites last_review_time on every push.
"""

import dataclasses
import re

from anki.collection import Collection

from scripts.ankisync import bridge
from scripts.ankisync.merge import MasterCard, Sched

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


class TestStudyNoteTypes:
    """Clozes and code cards: their note types, made on demand, and the exercise that travels hidden."""

    EXERCISE = '{"kind":"fill","source":"x = {{c1::Foo::Bar.new({ a: { b: 1 }})}}"}'
    CLOZE_FRONT = "Do it.<br><pre><code>x = {{c1::Foo&#58;&#58;Bar.new({ a: { b: 1 &#125;&#125;)}}\ny</code></pre>"

    def _master(self, **fields):
        sched = Sched(due=None, stability=None, difficulty=None, reps=0, lapses=0, state=0,
                      last_review=None, interval=0.0)
        return MasterCard(id=CUID, tags=("ruby",), deck="Default", suspended=False, sched=sched, **fields)

    def test_a_plain_card_stays_basic(self, tmp_path):
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front="F", back="B"))
            assert col.get_note(nid).note_type()["name"] == "Basic"
            assert col.models.by_name(bridge.STUDY_CLOZE) is None
        finally:
            col.close()

    def test_a_card_with_no_exercise_never_gets_a_cloze_note_type(self, tmp_path):
        # flashcard-mcp refuses such a card. Were one ever to arrive, Anki shows its braces as text
        # rather than making cards the sync keeps no schedule for.
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front="A {{c1::x}}", back="B"))
            assert col.get_note(nid).note_type()["name"] == "Basic"
            assert col.models.by_name(bridge.STUDY_CLOZE) is None
        finally:
            col.close()

    def test_a_cloze_with_all_its_blanks_is_one_card(self, tmp_path):
        col = _collection(tmp_path)
        try:
            front = "A {{c1::x}} and a {{c1::y}}."
            nid = bridge.create_card(col, self._master(front=front, back="B", exercise=self.EXERCISE))
            assert col.get_note(nid).note_type()["name"] == bridge.STUDY_CLOZE
            (cid,) = col.card_ids_of_note(nid)
            assert "[...]" in col.get_card(cid).question()
            answer = col.get_card(cid).answer()
            assert "x" in answer and "y" in answer and "B" in answer
        finally:
            col.close()

    def test_code_with_braces_and_colons_survives_the_cloze_parser(self, tmp_path):
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front=self.CLOZE_FRONT, back="B", exercise=self.EXERCISE))
            card = col.get_card(col.card_ids_of_note(nid)[0])
            # Anki keeps the deletion in an attribute of its [...], for its own scripts.
            shown = re.sub(r'data-cloze="[^"]*"', "", card.question())
            assert "Foo" not in shown and "[...]" in shown
            assert "&#58;&#58;Bar.new({ a: { b: 1 &#125;&#125;)" in card.answer()
        finally:
            col.close()

    def test_the_exercise_comes_back_and_no_template_shows_it(self, tmp_path):
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front=self.CLOZE_FRONT, back="B", exercise=self.EXERCISE))
            (read,) = bridge.read_anki_cards(col)
            assert read.exercise == self.EXERCISE
            assert read.front == self.CLOZE_FRONT
            card = col.get_card(col.card_ids_of_note(nid)[0])
            assert '"kind"' not in card.question() and '"kind"' not in card.answer()
        finally:
            col.close()

    def test_a_compose_card_is_front_and_back_with_the_exercise(self, tmp_path):
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front="<pre>___</pre>", back="B", exercise=self.EXERCISE))
            assert col.get_note(nid).note_type()["name"] == bridge.STUDY_CODE
            (read,) = bridge.read_anki_cards(col)
            assert read.exercise == self.EXERCISE
            assert read.back == "B"
        finally:
            col.close()

    def test_an_edit_reaches_the_hidden_field(self, tmp_path):
        col = _collection(tmp_path)
        try:
            nid = bridge.create_card(col, self._master(front=self.CLOZE_FRONT, back="B", exercise=self.EXERCISE))
            bridge.update_content(col, nid, self._master(front=self.CLOZE_FRONT, back="C", exercise='{"new":1}'))
            (read,) = bridge.read_anki_cards(col)
            assert (read.back, read.exercise) == ("C", '{"new":1}')
        finally:
            col.close()

    def test_a_second_card_reuses_the_note_type(self, tmp_path):
        col = _collection(tmp_path)
        try:
            bridge.create_card(col, self._master(front="{{c1::a}}", back="", exercise=self.EXERCISE))
            before = len(col.models.all_names_and_ids())
            other = dataclasses.replace(self._master(front="{{c1::b}}", back="", exercise=self.EXERCISE), id=CUID + "x")
            bridge.create_card(col, other)
            assert len(col.models.all_names_and_ids()) == before
        finally:
            col.close()


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
