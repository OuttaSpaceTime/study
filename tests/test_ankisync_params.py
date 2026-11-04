"""Anki's scheduling options are mirrored into flashcard-mcp's Config row."""

import sqlite3

import pytest
from anki.collection import Collection

from scripts.ankisync import params


@pytest.fixture
def col(tmp_path):
    c = Collection(str(tmp_path / "c.anki2"))
    yield c
    c.close()


def test_defaults_are_ankis(col):
    assert params.read_options(col) == {
        "learningSteps": "1m,10m",
        "relearningSteps": "10m",
        "requestRetention": 0.9,
        "fsrsWeights": "",
    }


def test_changed_options_are_read_and_written(col):
    conf = col.decks.get_config(1)
    conf["new"]["delays"] = [2, 30, 1440]
    conf["lapse"]["delays"] = [15]
    conf["desiredRetention"] = 0.85
    col.decks.update_config(conf)

    opts = params.read_options(col)
    assert opts["learningSteps"] == "2m,30m,1d"
    assert opts["relearningSteps"] == "15m"
    assert opts["requestRetention"] == 0.85

    con = sqlite3.connect(":memory:")
    con.execute("create table Config(id, learningSteps, relearningSteps, requestRetention, fsrsWeights)")
    con.execute("insert into Config values('default','1m,10m','10m',0.9,'')")
    assert params.write_options(con, opts) == ["learningSteps", "relearningSteps", "requestRetention"]
    assert params.write_options(con, opts) == []  # nothing changed the second time


def test_no_config_row_yet_writes_nothing():
    con = sqlite3.connect(":memory:")
    con.execute("create table Config(id, learningSteps, relearningSteps, requestRetention, fsrsWeights)")
    assert params.write_options(con, {"learningSteps": "1m", "relearningSteps": "1m", "requestRetention": 0.9, "fsrsWeights": ""}) == []


def test_a_sub_minute_step_stays_in_minutes_since_ts_fsrs_has_no_seconds():
    assert params._fmt_step(0.5) == "0.5m"
    assert params._fmt_step(1) == "1m"
    assert params._fmt_step(90) == "90m"
    assert params._fmt_step(60) == "1h"
    assert params._fmt_step(2880) == "2d"


def test_no_steps_are_read_as_none_not_as_the_defaults(col):
    conf = col.decks.get_config(1)
    conf["new"]["delays"] = []
    conf["lapse"]["delays"] = []
    col.decks.update_config(conf)
    opts = params.read_options(col)
    assert (opts["learningSteps"], opts["relearningSteps"]) == ("", "")
