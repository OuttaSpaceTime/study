"""Anki's scheduling options are mirrored into agentic-spaced-repetition's Config row."""

import pytest
from anki.collection import Collection
from conftest import FakeDeck

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
        "easyDays": "",
        "newPerDay": 20,
        "reviewsPerDay": 200,
        "newCardsIgnoreReviewLimit": 0,
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

    deck = FakeDeck(apply_result={"schedulerOptions": ["learningSteps", "relearningSteps", "requestRetention"]})
    assert params.sync_options(col, deck) == "options: learningSteps, relearningSteps, requestRetention updated"
    (call,) = deck.applied()
    assert call["scheduler_options"] == opts


def test_nothing_changed_is_one_quiet_line(col):
    deck = FakeDeck(apply_result={"schedulerOptions": []})
    assert params.sync_options(col, deck) == "options: unchanged"


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


def test_easy_days_are_read_monday_first(col):
    conf = col.decks.get_config(1)
    conf["easyDaysPercentages"] = [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]
    col.decks.update_config(conf)
    assert params.read_options(col)["easyDays"] == "[1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0]"


def test_daily_limits_and_the_collection_wide_switch_are_read(col):
    conf = col.decks.get_config(1)
    conf["new"]["perDay"] = 5
    conf["rev"]["perDay"] = 50
    col.decks.update_config(conf)
    col.set_config("newCardsIgnoreReviewLimit", True)
    opts = params.read_options(col)
    assert (opts["newPerDay"], opts["reviewsPerDay"], opts["newCardsIgnoreReviewLimit"]) == (
        5,
        50,
        1,
    )
