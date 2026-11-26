"""Shared fixtures for wiki tests."""

import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.deck.client import CardRecord, ReviewRecord


@pytest.fixture
def wiki_dir(tmp_path: Path) -> Path:
    """Create a temporary wiki directory with an empty index."""
    wd = tmp_path / "wiki"
    wd.mkdir()
    (wd / ".wiki-index.json").write_text("{}\n")
    return wd


@pytest.fixture
def sample_page(wiki_dir: Path) -> Path:
    """Write a sample wiki page and return its path."""
    page_dir = wiki_dir / "git"
    page_dir.mkdir()
    page = page_dir / "test-page.md"
    page.write_text(textwrap.dedent("""\
        ---
        title: "test page"
        aliases: [test alias, another alias]
        tags: [git, testing]
        category: work
        created: 2026-04-09
        updated: 2026-04-09
        source_skill: study-walkthrough
        flashcard_ids: [cmne7xz9202lx0msonsbfhp3j, cmne7xz1y02k30msouw64srcz, cmne7xyv602if0msoa0ryw0o7]
        ---

        # test page

        ## Section One

        Content here.

        ## Section Two

        More content.
    """))
    return page


# ---- the deck, without a deck server ---------------------------------------------------
# Everything that reaches the flashcard deck goes through scripts.deck.client.DeckClient, so
# tests stand a FakeDeck in for it: it records the calls and answers from canned records.
# What the real server does with a call is flashcard-mcp's test suite's business, and
# tests/test_deck_contract.py checks that the two still agree.
EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def make_card(card_id: str = "c1", **over) -> CardRecord:
    fields = dict(
        id=card_id, deck_id="d1", deck="Software Engineering", front=f"Q {card_id}?", back="An answer.",
        tags=(), type="guided", exercise=None, suspended=False, due=EPOCH, stability=10.0, difficulty=5.0,
        reps=3, lapses=0, state=2, last_review=EPOCH, interval=10.0, inherited_from=None,
        created_at=EPOCH, updated_at=EPOCH,
    )
    return CardRecord(**{**fields, **over})


def make_review(card_id: str, reviewed_at: datetime, rating: int = 3, **over) -> ReviewRecord:
    return ReviewRecord(**{**dict(card_id=card_id, reviewed_at=reviewed_at, rating=rating, response_ms=None,
                                  state=None), **over})


class FakeDeck:
    """A DeckClient that answers from the cards, reviews and tombstones it was given.

    `sync_apply` only records its call and returns a canned result: what the real deck does with
    a plan (the cascade of a deletion, the tombstone, the fallback memory state) is tested in
    flashcard-mcp's sync-apply.test.ts, not simulated here.
    """

    def __init__(self, cards=(), reviews=(), tombstones=(), apply_result=None):
        self.cards = list(cards)
        self.reviews = list(reviews)
        self._tombstones = set(tombstones)
        self.apply_result = apply_result
        self.calls: list[tuple[str, dict]] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def card_records(self, ids=None, inherited_from=None, include_suspended=True):
        self.calls.append(("card_records", {"ids": ids, "inherited_from": inherited_from,
                                            "include_suspended": include_suspended}))
        wanted = None if ids is None else set(ids)
        return [c for c in self.cards
                if (wanted is None or c.id in wanted)
                and (inherited_from is None or c.inherited_from == inherited_from)
                and (include_suspended or not c.suspended)]

    def review_records(self, card_ids=None):
        self.calls.append(("review_records", {"card_ids": card_ids}))
        return [r for r in self.reviews if card_ids is None or r.card_id in set(card_ids)]

    def tombstones(self):
        self.calls.append(("tombstones", {}))
        return set(self._tombstones)

    def sync_apply(self, **plan):
        plan.pop("timeout", None)  # how long the caller will wait is not part of the plan
        self.calls.append(("sync_apply", plan))
        if self.apply_result is not None:
            return self.apply_result
        return {"schedules": len(plan.get("schedules") or []), "reviews": len(plan.get("reviews") or []),
                "reviewsSkipped": {"present": 0, "noCard": 0},
                "imports": {"imported": len(plan.get("imports") or []), "rejected": []},
                "deletions": len(plan.get("deletions") or []), "schedulerOptions": []}

    def applied(self) -> list[dict]:
        return [plan for name, plan in self.calls if name == "sync_apply"]
