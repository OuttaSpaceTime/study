"""Anki-side operations on the headless bridge collection.

Uses fastanki's patched Collection (profile open + AnkiWeb sync) and the
official `anki` package for everything else. The bridge profile is dedicated
to this sync — the desktop profile (User 1) is never touched.
"""

import subprocess
from datetime import UTC, datetime

# importing fastanki.core applies its Collection patches (open/sync/save_auth)
import fastanki.core  # noqa: F401
from anki.cards import FSRSMemoryState
from anki.collection import Collection

from scripts.ankisync.convert import (
    STATE_NEW,
    anki_due_to_dt,
    dt_to_anki_due,
    state_to_anki,
)
from scripts.ankisync.merge import DELETED_TAG, AnkiCard, MasterCard, Review, Sched

PROFILE = "StudySync"
NOTETYPE = "Basic"


def open_bridge() -> Collection:
    return Collection.open(PROFILE)


def lookup_password() -> str | None:
    """AnkiWeb password from the system keyring (GNOME keyring via secret-tool)."""
    res = subprocess.run(
        ["secret-tool", "lookup", "service", "ankiweb"], capture_output=True, text=True
    )
    return res.stdout.strip() or None


def _col_crt(col: Collection) -> datetime:
    return datetime.fromtimestamp(col.db.scalar("select crt from col"), tz=UTC)


def _newest_reviews(col: Collection) -> dict[int, int]:
    """Newest real review per Anki card id, in epoch ms (the revlog id).

    Authoritative over the card's last_review_time wherever it exists: an
    AnkiWeb sync-down delivers a remote review as a revlog row without setting
    last_review_time, and write_sched overwrites that field from master on
    every push, so the field alone can read as null or stale on a card Anki
    reviewed most recently. Ease 0 rows are reschedules, not reviews.
    """
    return dict(
        col.db.all("select cid, max(id) from revlog where ease between 1 and 4 group by cid")
    )


def read_anki_cards(col: Collection) -> list[AnkiCard]:
    crt = _col_crt(col)
    newest_review = _newest_reviews(col)
    out = []
    for nid in col.find_notes(""):
        note = col.get_note(nid)
        cids = col.card_ids_of_note(nid)
        if not cids:
            continue
        card = col.get_card(cids[0])
        ms = card.memory_state
        reviewed_ms = newest_review.get(card.id)
        if reviewed_ms:
            last_review = datetime.fromtimestamp(reviewed_ms / 1000, tz=UTC)
        elif card.last_review_time:
            last_review = datetime.fromtimestamp(card.last_review_time, tz=UTC)
        else:
            last_review = None
        out.append(
            AnkiCard(
                note_id=nid,
                card_id=card.id,
                guid=note.guid,
                front=note.fields[0] if note.fields else "",
                back=note.fields[1] if len(note.fields) > 1 else "",
                tags=tuple(note.tags),
                deck=col.decks.name(card.did),
                suspended=card.queue == -1,
                sched=Sched(
                    due=(
                        None
                        if card.type == STATE_NEW
                        else anki_due_to_dt(card.due, state=card.type, col_crt=crt)
                    ),
                    stability=ms.stability if ms else None,
                    difficulty=ms.difficulty if ms else None,
                    reps=card.reps,
                    lapses=card.lapses,
                    state=card.type,
                    last_review=last_review,
                    interval=float(card.ivl),
                ),
            )
        )
    return out


def _deck_id(col: Collection, name: str) -> int:
    did = col.decks.id_for_name(name)
    if did is None:
        did = col.add_deck(name).id
    return did


def create_card(col: Collection, card: MasterCard) -> int:
    """Create note (guid = master CUID) and write its scheduling. Returns note id."""
    note = col.new_note(col.models[NOTETYPE])
    note.guid = card.id
    note.fields[0] = card.front
    note.fields[1] = card.back
    note.tags = list(card.tags)
    col.add_note(note, _deck_id(col, card.deck))
    for cid in col.card_ids_of_note(note.id):
        write_sched(col, cid, card)
    return note.id


def update_content(col: Collection, note_id: int, card: MasterCard) -> None:
    note = col.get_note(note_id)
    note.fields[0] = card.front
    note.fields[1] = card.back
    note.tags = list(card.tags)
    col.update_note(note)
    target = _deck_id(col, card.deck)
    for cid in col.card_ids_of_note(note_id):
        c = col.get_card(cid)
        if c.did != target:
            col.set_deck([cid], target)


def write_sched(col: Collection, card_id: int, card: MasterCard) -> None:
    sched = card.sched
    c = col.get_card(card_id)
    ctype, queue = state_to_anki(sched.state, card.suspended)
    c.type, c.queue = ctype, queue
    if sched.due is not None and sched.state != STATE_NEW:
        c.due = dt_to_anki_due(sched.due, state=sched.state, col_crt=_col_crt(col))
    c.ivl = int(round(sched.interval))
    c.reps = sched.reps
    c.lapses = sched.lapses
    if sched.stability is not None and sched.difficulty is not None:
        c.memory_state = FSRSMemoryState(
            stability=sched.stability, difficulty=sched.difficulty
        )
    if sched.last_review is not None:
        c.last_review_time = int(sched.last_review.timestamp())
    col.update_card(c)


def set_suspended(col: Collection, card_id: int, suspended: bool) -> None:
    if suspended:
        col.sched.suspend_cards([card_id])
    else:
        col.sched.unsuspend_cards([card_id])


def tag_deleted(col: Collection, note_ids: list[int]) -> None:
    """Mark a note deleted and suspend its cards, instead of removing it.

    The note is how the deletion reaches the other machines: they share only the
    AnkiWeb collection, so a removed note would be indistinguishable from one that
    was never created there. Suspending keeps it out of review in the meantime.
    """
    for note_id in note_ids:
        note = col.get_note(note_id)
        note.tags = [*note.tags, DELETED_TAG]
        col.update_note(note)
        col.sched.suspend_cards(col.card_ids_of_note(note_id))


def read_anki_reviews(col: Collection, guid_by_cid: dict[int, str]) -> list[Review]:
    rows = col.db.all("select id, cid, ease, time from revlog where ease between 1 and 4")
    out = []
    for rid, cid, ease, time_ms in rows:
        guid = guid_by_cid.get(cid)
        if guid is None:
            continue
        out.append(
            Review(
                card_id=guid,
                reviewed_at=datetime.fromtimestamp(rid / 1000, tz=UTC),
                rating=ease,
                response_ms=time_ms or None,
            )
        )
    return out


def append_revlog(col: Collection, reviews: list[Review], cid_by_guid: dict[str, int]) -> int:
    """Append master reviews to Anki's revlog (usn=-1 marks them for upload)."""
    added = 0
    for rev in reviews:
        cid = cid_by_guid.get(rev.card_id)
        if cid is None:
            continue
        rid = int(rev.reviewed_at.timestamp() * 1000)
        while col.db.scalar("select 1 from revlog where id = ?", rid):
            rid += 1  # revlog PK is a global ms timestamp; bump on collision
        col.db.execute(
            """insert into revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
               values (?, ?, -1, ?, 0, 0, 0, ?, 1)""",
            rid,
            cid,
            rev.rating,
            rev.response_ms or 0,
        )
        added += 1
    return added


def sync_remote(
    col: Collection,
    user: str | None,
    passw: str | None,
    media: bool = False,
    upload: bool = False,
):
    # upload=True resolves a forced full sync by uploading the bridge to AnkiWeb
    # (first sync against an empty account); default resolves by downloading.
    return col.sync(user=user, passw=passw, media=media, upload=upload)
