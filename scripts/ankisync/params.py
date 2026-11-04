"""Mirror Anki's scheduling options into flashcard-mcp's Config row.

The deck server schedules with ts-fsrs and shows the rating keys' intervals,
so it must use the options Anki uses or the two disagree ("Good" 10m here, 6d
there). The bridge collection has the desktop's deck options after a sync
down, so they are read from it on every sync and written to master.db's
Config: learning and relearning steps, desired retention and the FSRS weights.
Only these four columns are ever written, and only when they differ.

One preset is used for everything: the one most cards' decks point at. The
study repo keeps all its decks on one preset; a deck with its own would need
per-deck settings in the deck server first.
"""

import json
import sqlite3
from collections import Counter

from anki.collection import Collection

from scripts.ankisync import master

# FSRS-6 weights have 21 values, FSRS-5's 19, and ts-fsrs takes both. Anki keeps
# empty params until the user optimizes, which means "its defaults", the same as
# ts-fsrs's.
_WEIGHT_COUNTS = (21, 19)


def _fmt_step(minutes: float) -> str:
    """Anki stores steps in minutes; ts-fsrs wants "1m", "10m", "1h", "1d", and has no seconds."""
    if minutes >= 1440 and minutes % 1440 == 0:
        return f"{int(minutes // 1440)}d"
    if minutes >= 60 and minutes % 60 == 0:
        return f"{int(minutes // 60)}h"
    return f"{minutes:g}m"  # a sub-minute step stays in minutes: 0.5 -> 0.5m


def read_options(col: Collection) -> dict | None:
    """The scheduling options of the preset most decks use, or None if unreadable."""
    counts = Counter()
    for deck in col.decks.all_names_and_ids(include_filtered=False):
        counts[col.decks.config_dict_for_deck_id(deck.id)["id"]] += 1
    if not counts:
        return None
    conf = col.decks.get_config(counts.most_common(1)[0][0])
    if conf is None:
        return None
    proto = col._backend.get_deck_config(conf["id"])
    cfg = proto.config
    weights = list(cfg.fsrs_params_6) or list(cfg.fsrs_params_5)
    return {
        # No steps is a setting, and read as Anki reads it: straight to the first review.
        "learningSteps": ",".join(_fmt_step(m) for m in cfg.learn_steps),
        "relearningSteps": ",".join(_fmt_step(m) for m in cfg.relearn_steps),
        "requestRetention": round(cfg.desired_retention, 4) or 0.9,
        "fsrsWeights": json.dumps([round(w, 8) for w in weights]) if len(weights) in _WEIGHT_COUNTS else "",
    }


def write_options(con: sqlite3.Connection, opts: dict) -> list[str]:
    """Write the options that changed to Config; returns the changed column names."""
    row = con.execute(
        "select learningSteps, relearningSteps, requestRetention, fsrsWeights from Config where id = 'default'"
    ).fetchone()
    if row is None:  # the deck server creates it on first use; nothing to mirror into yet
        return []
    names = ["learningSteps", "relearningSteps", "requestRetention", "fsrsWeights"]
    changed = [n for n, old in zip(names, row, strict=True) if old != opts[n]]
    for n in changed:
        con.execute(f"update Config set {n} = ? where id = 'default'", (opts[n],))  # noqa: S608 - n is from the fixed list
    return changed


def sync_options(col: Collection) -> str:
    """Read from Anki, write to master.db; a one-line note for the sync output."""
    opts = read_options(col)
    if opts is None:
        return "options: unreadable, kept"
    with master.connect(readonly=False) as con, con:
        changed = write_options(con, opts)
    return f"options: {', '.join(changed)} updated" if changed else "options: unchanged"
