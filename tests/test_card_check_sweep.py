"""scripts/card-check-sweep's decisions. The sweep itself runs the real skill, on the subscription."""

import datetime
import importlib.machinery
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("card_check_sweep", str(ROOT / "scripts" / "card-check-sweep"))
spec = importlib.util.spec_from_loader("card_check_sweep", loader)
sweep = importlib.util.module_from_spec(spec)
loader.exec_module(sweep)

NOW = datetime.datetime(2026, 11, 4, 9, 0)


def test_only_a_back_saying_too_much_goes_to_the_cheap_model():
    assert sweep.model_for(["extra_info"]) == "haiku"
    for issues in (["not_atomic"], ["incorrect"], ["extra_info", "ambiguous_front"], []):
        assert sweep.model_for(issues) == "sonnet"


def test_a_limit_lifts_when_it_says_with_some_grace():
    assert sweep.limit_lifts("You've hit your 5-hour limit · resets 1:30pm (Europe/Berlin)", NOW) == NOW.replace(hour=13, minute=32)
    assert sweep.limit_lifts("resets 8:30am", NOW) == NOW.replace(day=5, hour=8, minute=32), "already past today: tomorrow"
    assert sweep.limit_lifts("resets 12am", NOW) == NOW.replace(day=5, hour=0, minute=2)


def test_a_time_just_past_means_lifted_not_tomorrow():
    now = NOW.replace(hour=13, minute=32, second=3)
    assert sweep.limit_lifts("You've hit your 5-hour limit · resets 1:30pm (Europe/Berlin)", now) == now + sweep.GRACE


def test_a_limit_with_no_time_waits_an_hour():
    assert sweep.limit_lifts("rate limited", NOW) == NOW + datetime.timedelta(hours=1)


def test_a_limit_is_told_from_other_failures():
    assert sweep.is_limit("You've hit your 5-hour limit · resets 8:30am (Europe/Berlin)")
    assert sweep.is_limit("Claude usage limit reached")
    assert not sweep.is_limit("the card failed the limit of 200 characters")


def test_the_work_is_what_fails_now_wrong_backs_then_lapses_first():
    cards = [{"id": i, "lapses": n} for i, n in (("a", 0), ("b", 5), ("c", 1), ("sound", 9), ("stuck", 9))]
    verdicts = {"a": ["incorrect"], "b": ["extra_info"], "c": ["extra_info"], "sound": [], "stuck": ["not_atomic"]}
    assert [c["id"] for c in sweep.wanted(cards, verdicts, {"stuck"})] == ["a", "b", "c"]
    assert "stuck" in [c["id"] for c in sweep.wanted(cards, verdicts, {"stuck"}, retry=True)]


def test_a_batched_card_carries_what_the_session_needs_and_the_verdict(monkeypatch):
    monkeypatch.setattr(sweep.gate, "run_judge", lambda card: {
        "asked": ["a", "b"], "claims": [{"text": "x", "role": "extra"}, {"text": "y", "role": "answer"}], "issues": []})
    card = {"id": "c", "deckId": "d", "tags": "t", "type": "guided", "front": "F", "back": "B"}
    out = sweep.batch_card(card, ["a part"])
    assert (out["deckId"], out["tags"], out["type"]) == ("d", "t", "guided")
    assert out["asked"] == ["a", "b"] and out["extra"] == ["x"]
    assert {f["issue"] for f in out["flaws"]} == {"not_atomic", "extra_info"}
    assert out["already_has_parts"] == ["a part"]


# ---- what it won't try again ------------------------------------------------------------
def card(i, front="F", back="B", exercise=None):
    return {"id": i, "front": front, "back": back, "exercise": exercise, "lapses": 0}


def results(tmp_path, monkeypatch, *rows):
    path = tmp_path / "results.jsonl"
    path.write_text("".join(r + "\n" if isinstance(r, str) else json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(sweep, "RESULTS", path)


def test_a_card_that_could_not_be_fixed_is_left_while_it_reads_the_same(tmp_path, monkeypatch):
    results(tmp_path, monkeypatch, {"id": "a", "outcome": "unchanged", "front": "F", "back": "B"})
    assert sweep.gave_up_on([card("a")]) == {"a"}


def test_a_card_edited_since_is_tried_again(tmp_path, monkeypatch):
    results(tmp_path, monkeypatch, {"id": "a", "outcome": "unchanged", "front": "F", "back": "B"})
    assert sweep.gave_up_on([card("a", back="Shorter")]) == set()


def test_only_the_last_word_on_a_card_counts(tmp_path, monkeypatch):
    results(tmp_path, monkeypatch, {"id": "a", "outcome": "failed", "front": "F", "back": "B"},
            {"id": "a", "outcome": "fixed", "front": "F", "back": "B"})
    assert sweep.gave_up_on([card("a")]) == set()


def test_a_torn_last_line_costs_only_that_line(tmp_path, monkeypatch):
    results(tmp_path, monkeypatch, {"id": "a", "outcome": "unchanged", "front": "F", "back": "B"}, '{"id": "b", "outc')
    assert sweep.gave_up_on([card("a")]) == {"a"}


# ---- a run, with the skill and the judge faked ---------------------------------------------
def args(**over):
    return SimpleNamespace(**{"dry_run": False, "no_wait": False, "retry": False, "one_session": False,
                              "limit": None, "workers": 1, **over})


def faked(tmp_path, monkeypatch, cards):
    monkeypatch.setattr(sweep, "RESULTS", tmp_path / "results.jsonl")
    monkeypatch.setattr(sweep, "deck", lambda: cards)
    monkeypatch.setattr(sweep, "judge_all", lambda c, w, wait: {x["id"]: ["not_atomic"] for x in c})
    relinks = []
    monkeypatch.setattr(sweep, "relink", lambda: relinks.append(1))
    return relinks


def test_a_limit_with_no_wait_stops_with_status_3_and_relinks_what_it_did(tmp_path, monkeypatch):
    relinks = faked(tmp_path, monkeypatch, [card("a")])

    def limited(_):
        raise sweep.UsageLimit("limit")

    monkeypatch.setattr(sweep, "one_session", limited)
    assert sweep.sweep(args(one_session=True, no_wait=True)) == 3
    assert relinks


def test_one_session_takes_the_plain_cards_and_leaves_the_code_cards_to_the_per_card_way(tmp_path, monkeypatch):
    faked(tmp_path, monkeypatch, [card("plain"), card("code", exercise="{}")])
    batched, fixed = [], []
    monkeypatch.setattr(sweep, "one_session", lambda plain: batched.extend(c["id"] for c in plain))
    monkeypatch.setattr(sweep, "fix", lambda i, issues: fixed.append(i) or {"outcome": "fixed", "summary": "ok"})
    assert sweep.sweep(args(one_session=True)) == 0
    assert (batched, fixed) == (["plain"], ["code"])


def test_a_limit_is_waited_out_and_the_run_starts_over(tmp_path, monkeypatch):
    faked(tmp_path, monkeypatch, [card("a")])
    tries = []

    def limited_once(_):
        tries.append(1)
        if len(tries) == 1:
            raise sweep.UsageLimit("resets 9am")

    monkeypatch.setattr(sweep, "one_session", limited_once)
    monkeypatch.setattr(sweep, "sleep_past", lambda message: None)
    assert sweep.sweep(args(one_session=True)) == 0
    assert len(tries) == 2
