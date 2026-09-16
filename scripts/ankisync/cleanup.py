"""card-htmlize CLI — canonicalize all master.db cards to simple Anki HTML.

Dry-run by default (summary + samples); --apply backs up master.db first,
then rewrites front/back in one transaction. Idempotent: converted cards
are detected as HTML and skipped on later runs.
"""

import argparse
import shutil
import sys
from datetime import datetime

from scripts.ankisync.htmlize import to_anki_html
from scripts.ankisync.master import connect, db_path


def _changes(con):
    for card_id, front, back in con.execute("SELECT id, front, back FROM Card"):
        new_front, new_back = to_anki_html(front or ""), to_anki_html(back or "")
        if new_front != front or new_back != back:
            yield card_id, front, back, new_front, new_back


def main() -> None:
    p = argparse.ArgumentParser(prog="card-htmlize", description=__doc__)
    p.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    p.add_argument("--samples", type=int, default=3, help="sample diffs to show in dry-run")
    args = p.parse_args()

    if not args.apply:
        with connect(readonly=True) as con:
            changes = list(_changes(con))
        print(f"dry-run: {len(changes)} card(s) would change")
        for _id, front, _back, new_front, new_back in changes[: args.samples]:
            print(f"--- {_id}")
            print(f"  front: {front[:80]!r}")
            print(f"      -> {new_front[:80]!r}")
            print(f"  back-> {new_back[:120]!r}")
        sys.exit(0)

    db = db_path()
    backup = db.with_name(
        f"master.db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"  # noqa: DTZ005
    )
    shutil.copy2(db, backup)
    with connect(readonly=False) as con, con:
        # materialize before writing: updating rows while the SELECT cursor is
        # still iterating the same table makes sqlite skip rows
        changes = list(_changes(con))
        for card_id, _f, _b, new_front, new_back in changes:
            con.execute(
                "UPDATE Card SET front = ?, back = ? WHERE id = ?",
                (new_front, new_back, card_id),
            )
    print(f"applied: {len(changes)} card(s) rewritten (backup: {backup.name})")
    sys.exit(0)
