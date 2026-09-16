"""Stateless sync planning — pure decision logic, no I/O.

Direction contract:
- master.db owns card existence and content (one-way push to Anki, master wins).
- Scheduling flows both ways: the side with the newer last review wins wholesale.
- Review history is append-only: union by (card, timestamp), nothing overwritten.
- Anki-only notes (non-CUID guid) are reported, never imported into master.

Deletion is explicit state on both sides, never inferred from absence. Absence is
ambiguous in both directions: a note missing from Anki is either brand new here or
deleted elsewhere, and a card missing from master is either never seen here or
deleted here. Several machines share one AnkiWeb collection, so guessing either way
destroys data. Instead a deleted card keeps its Anki note, tagged DELETED_TAG, and
master keeps a tombstone row; absence then means exactly one thing on each side.

  local \\ remote   LIVE (note)        DEL (tagged)        NONE
  LIVE (row)        content + sched    soft-delete here    create on Anki
  TOMB (tombstone)  tag the note       nothing             nothing
  NONE              import             tombstone here      nothing

No sync bookkeeping exists: every decision derives from the current state of both
sides. Identity is carried by the Anki note guid, which we set to the master card's
CUID at creation time (the same convention flashcard-mcp's .apkg export uses).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

CUID_RE = re.compile(r"^c[a-z0-9]{20,}$")

DELETED_TAG = "__deleted__"


def is_cuid(guid: str) -> bool:
    """True if a guid has the shape of a Prisma CUID (i.e. a card that was ours).

    Anki's native guids are 10-char mixed-case base91 strings, so they never match.
    """
    return bool(CUID_RE.match(guid))


@dataclass(frozen=True)
class Sched:
    """Scheduling state in master.db units (datetimes, FSRS floats)."""

    due: datetime | None
    stability: float | None
    difficulty: float | None
    reps: int
    lapses: int
    state: int  # ts-fsrs: 0 new, 1 learning, 2 review, 3 relearning
    last_review: datetime | None
    interval: float  # days


@dataclass(frozen=True)
class MasterCard:
    id: str  # CUID; becomes the Anki note guid
    front: str
    back: str
    tags: tuple[str, ...]
    deck: str
    suspended: bool
    sched: Sched
    inherited: bool = False  # split off an existing card, so reps came with it


@dataclass(frozen=True)
class AnkiCard:
    note_id: int
    card_id: int
    guid: str
    front: str
    back: str
    tags: tuple[str, ...]
    deck: str
    suspended: bool
    sched: Sched


@dataclass(frozen=True)
class Review:
    """One review event; (card_id, reviewed_at) is the global natural key."""

    card_id: str
    reviewed_at: datetime
    rating: int  # 1-4 on both sides (ts-fsrs Grade == Anki ease)
    response_ms: int | None


@dataclass
class SyncPlan:
    create: list[MasterCard] = field(default_factory=list)
    update_content: list[tuple[MasterCard, int]] = field(default_factory=list)  # (card, note_id)
    push_sched: list[tuple[MasterCard, int]] = field(default_factory=list)  # (card, anki card_id)
    pull_sched: list[tuple[str, Sched]] = field(default_factory=list)  # (master card id, sched)
    push_suspend: list[tuple[MasterCard, int]] = field(default_factory=list)  # (card, card_id)
    tag_deleted: list[int] = field(default_factory=list)  # note ids to mark DELETED_TAG
    local_soft_delete: list["AnkiCard"] = field(default_factory=list)  # tombstone here
    unknown_anki: list[int] = field(default_factory=list)  # note ids not ours; report only
    import_from_anki: list["AnkiCard"] = field(default_factory=list)  # created on another machine


@dataclass
class HistoryPlan:
    pull_reviews: list[Review] = field(default_factory=list)  # append to master Review
    push_reviews: list[Review] = field(default_factory=list)  # append to Anki revlog


def _content(card: MasterCard | AnkiCard) -> tuple:
    # tags compared order- and case-insensitively: Anki sorts them and treats
    # casing as canonical-first-seen, so neither survives a push
    return (card.front, card.back, tuple(sorted(t.casefold() for t in card.tags)), card.deck)


def _is_deleted(anki: AnkiCard) -> bool:
    return DELETED_TAG in {t.casefold() for t in anki.tags}


def plan_sync(
    master_cards: list[MasterCard],
    anki_cards: list[AnkiCard],
    deleted_ids: set[str] | frozenset[str] = frozenset(),
) -> SyncPlan:
    plan = SyncPlan()
    master_by_id = {c.id: c for c in master_cards}
    anki_by_guid = {a.guid: a for a in anki_cards}

    for card in master_cards:
        anki = anki_by_guid.get(card.id)
        if anki is None:
            plan.create.append(card)
            continue
        if _is_deleted(anki):
            # deleted on another machine: take the deletion, never push our row back
            plan.local_soft_delete.append(anki)
            continue
        if _content(card) != _content(anki):
            plan.update_content.append((card, anki.note_id))
        _plan_sched(plan, card, anki)
        if card.suspended != anki.suspended:
            plan.push_suspend.append((card, anki.card_id))

    for anki in anki_cards:
        if anki.guid in master_by_id:
            continue
        if not is_cuid(anki.guid):
            plan.unknown_anki.append(anki.note_id)
        elif anki.guid in deleted_ids:
            if not _is_deleted(anki):
                plan.tag_deleted.append(anki.note_id)
        elif _is_deleted(anki):
            plan.local_soft_delete.append(anki)
        else:
            plan.import_from_anki.append(anki)

    return plan


def _plan_sched(plan: SyncPlan, card: MasterCard, anki: AnkiCard) -> None:
    # whole-second resolution: both sides carry millisecond precision but round
    # trip through second-granularity fields — sub-second deltas are not a newer review
    ours = int(card.sched.last_review.timestamp()) if card.sched.last_review else None
    theirs = int(anki.sched.last_review.timestamp()) if anki.sched.last_review else None
    if ours is None and theirs is None:
        return
    if theirs is None or (ours is not None and ours > theirs):
        plan.push_sched.append((card, anki.card_id))
    elif ours is None or theirs > ours:
        plan.pull_sched.append((card.id, anki.sched))


def _review_key(r: Review) -> tuple[str, int]:
    # Whole-second resolution: Anki's revlog PK is a global epoch-ms timestamp and
    # gets bumped +1ms on collision, so exact-ms keys would re-push forever.
    return (r.card_id, int(r.reviewed_at.timestamp()))


def plan_history(ours: list[Review], theirs: list[Review]) -> HistoryPlan:
    """Append-only union by (card_id, reviewed_at); nothing is ever overwritten."""
    our_keys = {_review_key(r) for r in ours}
    their_keys = {_review_key(r) for r in theirs}
    return HistoryPlan(
        pull_reviews=[r for r in theirs if _review_key(r) not in our_keys],
        push_reviews=[r for r in ours if _review_key(r) not in their_keys],
    )
