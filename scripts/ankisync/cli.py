"""anki-sync CLI — stateless one-way card push to AnkiWeb with scheduling pull-back.

Commands:
  login <email>   store AnkiWeb email; verify the keyring has the password
  sync            full sync cycle (down, merge, up); --dry-run to preview
  status          counts on both sides without syncing
"""

import argparse
import json
import sys

from fastanki.core import data_path

from scripts.ankisync import bridge, master
from scripts.ankisync.htmlize import to_anki_html
from scripts.ankisync.merge import is_cuid, plan_history, plan_sync

CONFIG = data_path() / bridge.PROFILE / "sync-config.json"


def _load_email() -> str | None:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text()).get("email")
    return None


def cmd_login(args) -> int:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({"email": args.email}) + "\n")
    if bridge.lookup_password():
        print(f"login: email saved ({args.email}); password found in keyring")
        return 0
    print(f"login: email saved ({args.email}); no password in keyring yet")
    print("store it (prompts on stdin, never lands in shell history):")
    print('  secret-tool store --label="AnkiWeb study sync" service ankiweb')
    return 1


def _gather(col):
    with master.connect(readonly=True) as con:
        cards = master.read_cards(con)
        reviews = master.read_reviews(con)
    anki_cards = bridge.read_anki_cards(col)
    ours_ids = {c.id for c in cards}
    # never plan: reviews of since-deleted cards (no note to land on) and
    # rating-0 skip events (Anki's ease range is 1-4; they can't round-trip)
    reviews = [r for r in reviews if r.card_id in ours_ids and 1 <= r.rating <= 4]
    # every CUID guid, not just ours_ids: an empty-master import (see merge.py)
    # needs an about-to-be-created card's review history too, not just existing ones
    guid_by_cid = {a.card_id: a.guid for a in anki_cards if is_cuid(a.guid)}
    anki_reviews = bridge.read_anki_reviews(col, guid_by_cid)
    return cards, reviews, anki_cards, anki_reviews


def _warn_format(cards) -> None:
    """Simple HTML is the only supported card format; flag drift on every run."""
    bad = sum(1 for c in cards if to_anki_html(c.front) != c.front or to_anki_html(c.back) != c.back)
    if bad:
        print(f"format: {bad} card(s) not in simple-HTML form — run scripts/card-htmlize")


def _reinstated(plan) -> int:
    """Creates that are really undeletes: master cards with reviews of their own
    that Anki no longer has a note for. Master owns existence, so a card deleted
    on the phone comes back on the next sync — worth saying out loud. A split
    inherits its parent's reps without ever having been pushed, so it is new."""
    return sum(1 for c in plan.create if c.sched.reps > 0 and not c.inherited)


def _summary(plan, hist) -> str:
    parts = []
    for label, items in (
        ("create", plan.create),
        ("import", plan.import_from_anki),
        ("content", plan.update_content),
        ("sched→anki", plan.push_sched),
        ("sched←anki", plan.pull_sched),
        ("suspend", plan.push_suspend),
        ("delete", plan.delete_notes),
        ("history→anki", hist.push_reviews),
        ("history←anki", hist.pull_reviews),
    ):
        if items:
            parts.append(f"{label} {len(items)}")
            if label == "create" and _reinstated(plan):
                parts[-1] += f" ({_reinstated(plan)} deleted on Anki, reinstated)"
    if plan.unknown_anki:
        parts.append(f"unknown(ignored) {len(plan.unknown_anki)}")
    return ", ".join(parts) if parts else "nothing to do"


def cmd_sync(args) -> int:
    email, passw = _load_email(), bridge.lookup_password()
    col = bridge.open_bridge()
    try:
        if not args.local:
            try:
                bridge.sync_remote(col, email, passw, media=args.media, upload=args.upload)
            except ValueError as e:
                print(f"sync: not logged in ({e}); run anki-sync login first")
                return 1

        cards, reviews, anki_cards, anki_reviews = _gather(col)
        _warn_format(cards)
        plan = plan_sync(cards, anki_cards)
        hist = plan_history(reviews, anki_reviews)
        print(f"plan: {_summary(plan, hist)}")
        if args.dry_run:
            return 0

        if plan.import_from_anki:
            imported_ids = {a.guid for a in plan.import_from_anki}
            sched_by_card = {a.guid: a.sched for a in plan.import_from_anki}
            imported_reviews = [r for r in hist.pull_reviews if r.card_id in imported_ids]
            with master.connect(readonly=False) as con, con:
                for anki_card in plan.import_from_anki:
                    master.import_card(con, anki_card)
                master.append_reviews(con, imported_reviews, sched_by_card)
            hist.pull_reviews = [r for r in hist.pull_reviews if r.card_id not in imported_ids]

        for card in plan.create:
            bridge.create_card(col, card)
        for card, note_id in plan.update_content:
            bridge.update_content(col, note_id, card)
        for card, cid in plan.push_sched:
            bridge.write_sched(col, cid, card)
        for card, cid in plan.push_suspend:
            bridge.set_suspended(col, cid, card.suspended)
        bridge.delete_notes(col, plan.delete_notes)
        if hist.push_reviews:
            fresh = bridge.read_anki_cards(col)  # creates may have added cards
            cid_by_guid = {a.guid: a.card_id for a in fresh if is_cuid(a.guid)}
            bridge.append_revlog(col, hist.push_reviews, cid_by_guid)

        if plan.pull_sched or hist.pull_reviews:
            sched_by_card = dict(plan.pull_sched)
            with master.connect(readonly=False) as con, con:
                for card_id, sched in plan.pull_sched:
                    master.apply_pull_sched(con, card_id, sched)
                master.append_reviews(con, hist.pull_reviews, sched_by_card)

        if not args.local:
            bridge.sync_remote(col, email, passw, media=args.media, upload=args.upload)
        print(f"sync: done ({_summary(plan, hist)})")
        return 0
    finally:
        col.close()


def cmd_status(args) -> int:
    col = bridge.open_bridge()
    try:
        cards, reviews, anki_cards, anki_reviews = _gather(col)
        _warn_format(cards)
        plan = plan_sync(cards, anki_cards)
        hist = plan_history(reviews, anki_reviews)
        print(f"master: {len(cards)} cards, {len(reviews)} reviews")
        print(f"bridge: {len(anki_cards)} notes, {len(anki_reviews)} reviews")
        print(f"pending: {_summary(plan, hist)}")
        return 0
    finally:
        col.close()


def main() -> None:
    p = argparse.ArgumentParser(prog="anki-sync", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("login", help="store AnkiWeb email; check keyring password")
    pl.add_argument("email")
    pl.set_defaults(fn=cmd_login)

    ps = sub.add_parser("sync", help="full sync cycle (down, merge, up)")
    ps.add_argument("--dry-run", action="store_true", help="plan only, change nothing")
    ps.add_argument("--local", action="store_true", help="skip AnkiWeb (bridge only)")
    ps.add_argument("--media", action="store_true", help="also sync media")
    ps.add_argument(
        "--upload",
        action="store_true",
        help="resolve a forced full sync by uploading the bridge (first sync)",
    )
    ps.set_defaults(fn=cmd_sync)

    pt = sub.add_parser("status", help="counts and pending plan, no changes")
    pt.set_defaults(fn=cmd_status)

    args = p.parse_args()
    sys.exit(args.fn(args))
