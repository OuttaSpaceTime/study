"""The card-quality gate (scripts/card-quality-gate), with a fake claude and a throwaway deck."""

import json
import os
import sqlite3
import stat
import subprocess
from pathlib import Path

import pytest

from scripts import card_quality as gate

ROOT = Path(__file__).resolve().parent.parent

CREATE = "mcp__flashcard-mcp__create_card"
UPDATE = "mcp__flashcard-mcp__update_card"

# Counts two things asked when the front has " and how ", an extra claim when the back says "RFC",
# flags "incorrect" when the back says 200 OK, fails when the front says "crash"; records each prompt it was given.
FAKE = """#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"prompt": prompt, "argv": sys.argv[1:], "key": os.environ.get("ANTHROPIC_API_KEY")}) + "\\n")
if "crash" in prompt:
    print("boom", file=sys.stderr); sys.exit(1)
issues = []
asked = ["what it is", "how to stop it"] if " and how " in prompt else ["one thing"]
claims = [{"text": "the answer", "role": "answer"}]
if "RFC" in prompt:
    claims.append({"text": "the RFC's number", "role": "extra"})
if "200 OK" in prompt:
    issues.append({"issue": "incorrect", "detail": "A matching ETag gets 304."})
if "no verdict" in prompt:
    print(json.dumps({"type": "result", "is_error": False, "subtype": "success", "result": ""})); sys.exit(0)
if "retries" in prompt:
    print(json.dumps({"type": "result", "is_error": False, "subtype": "error_max_structured_output_retries"})); sys.exit(0)
print(json.dumps({"type": "result", "is_error": False, "subtype": "success", "structured_output": {"asked": asked, "claims": claims, "issues": issues}}))
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake = tmp_path / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    db = tmp_path / "deck.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE Card (id TEXT PRIMARY KEY, front TEXT, back TEXT, exercise TEXT, inheritedFrom TEXT)")
    con.execute("INSERT INTO Card (id, front, back) VALUES ('c1', 'Which header revalidates an ETag?', '<code>If-None-Match</code>.')")
    con.execute("INSERT INTO Card (id, front, back, inheritedFrom) VALUES ('p1', 'A part', 'Of it', 'c1')")
    con.commit()
    con.close()
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("CARD_QUALITY_CLAUDE", str(fake))
    monkeypatch.setenv("FLASHCARD_MASTER_DB", str(db))
    monkeypatch.setenv("FAKE_LOG", str(log))
    monkeypatch.setenv("CARD_QUALITY_CACHE", str(tmp_path / "verdicts"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-reach-the-judge")
    return log


def calls(log):
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def decision(out):
    return out and out["hookSpecificOutput"]["permissionDecision"]


def test_a_sound_card_passes(env):
    assert gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is X?", "back": "Y."}}) is None
    (call,) = calls(env)
    assert "<front>\nWhat is X?\n</front>" in call["prompt"]
    assert call["argv"][call["argv"].index("--model") + 1] == "opus"
    assert call["argv"][call["argv"].index("--effort") + 1] == "high"
    assert call["key"] is None, "the judge runs on the subscription, not the API key"


def test_a_flawed_card_is_denied_with_its_flaws(env):
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is CSRF and how do you stop it?", "back": "x"}})
    assert decision(out) == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "not_atomic: It asks 2 things: what it is; how to stop it." in reason
    assert "split rather than drop" in reason


def test_a_fact_the_front_did_not_ask_for_is_denied(env):
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": "Which header revalidates an ETag?", "back": "If-None-Match, from RFC 7232."}})
    assert decision(out) == "deny"
    assert "extra_info: The back says more than the front asks: the RFC's number." in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_the_counts_decide_even_if_the_judge_names_no_issue():
    assert gate.verdict({"asked": ["a"], "claims": [{"text": "x", "role": "answer"}, {"text": "y", "role": "step"}], "issues": []}) == []
    (flaw,) = gate.verdict({"asked": ["a", "b"], "claims": [], "issues": []})
    assert flaw["issue"] == "not_atomic"
    (flaw,) = gate.verdict({"asked": ["a"], "claims": [{"text": "y", "role": "extra"}], "issues": []})
    assert flaw["issue"] == "extra_info"


def test_judging_a_stored_card_writes_nothing_and_reports_the_counts(env, capsys, monkeypatch):
    monkeypatch.setattr(gate.sys, "argv", ["card-quality-gate", "--judge", "c1"])
    gate.main()
    out = json.loads(capsys.readouterr().out)
    assert out["passes"] is True
    assert out["asked"] == ["one thing"]
    (call,) = calls(env)
    assert "Which header revalidates an ETag?" in call["prompt"]


def test_an_update_is_judged_with_the_stored_side(env):
    out = gate.decide({"tool_name": UPDATE, "tool_input": {"cardId": "c1", "back": "200 OK."}})
    assert decision(out) == "deny"
    (call,) = calls(env)
    assert "Which header revalidates an ETag?" in call["prompt"], "the front came from the deck"
    assert "200 OK." in call["prompt"]


def test_an_update_of_neither_side_is_not_judged(env):
    assert gate.decide({"tool_name": UPDATE, "tool_input": {"cardId": "c1", "tags": "http"}}) is None
    stored = {"cardId": "c1", "front": "Which header revalidates an ETag?", "back": "<code>If-None-Match</code>."}
    assert gate.decide({"tool_name": UPDATE, "tool_input": stored}) is None, "the sides as stored"
    assert calls(env) == []


def test_a_judge_that_fails_denies(env):
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": "crash", "back": "x"}})
    assert decision(out) == "deny"
    assert "could not judge" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_an_unknown_card_denies(env):
    out = gate.decide({"tool_name": UPDATE, "tool_input": {"cardId": "nope", "front": "Q?"}})
    assert decision(out) == "deny"


def test_other_tools_pass(env):
    assert gate.decide({"tool_name": "mcp__flashcard-mcp__delete_card", "tool_input": {"cardId": "c1"}}) is None
    assert gate.decide({}) is None
    assert calls(env) == []


def test_a_code_card_is_judged_on_what_it_asks_and_explains(env):
    exercise = {"kind": "predict", "brief": "What comes back?", "source": "r = [1].each {}", "explain": "Its receiver.",
                "cases": [{"expr": "r", "goal": "[1]"}]}
    out = gate.decide({"tool_name": "mcp__flashcard-mcp__create_code_card", "tool_input": {"exercise": exercise}})
    assert out is None
    prompt = calls(env)[-1]["prompt"]
    assert "What comes back?" in prompt and "r  # => {{c1::[1]}}" in prompt and "Its receiver." in prompt
    assert "kind predict" in prompt


def test_a_fill_cards_goals_are_in_plain_sight_as_the_developer_sees_them(env):
    exercise = {"kind": "fill", "brief": "Double it.", "source": "x = {{c1::2}}", "explain": "Why.",
                "cases": [{"expr": "x", "goal": "2"}]}
    gate.decide({"tool_name": "mcp__flashcard-mcp__create_code_card", "tool_input": {"exercise": exercise}})
    assert "x  # => 2" in calls(env)[-1]["prompt"]


def test_a_flawed_code_card_is_denied(env):
    exercise = {"brief": "What is it and how does it work?", "source": "", "explain": "x", "cases": []}
    out = gate.decide({"tool_name": "mcp__flashcard-mcp__update_code_card", "tool_input": {"exercise": exercise}})
    assert "not_atomic" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("tool_input", [
    {"front": "An origin is {{c1::this}}.", "back": "B"},
    {"front": "Q?", "back": "{{c1::A}}"},
    {"front": "<pre><code>{{c2::x}}</code></pre>", "back": "B"},
])
def test_a_cloze_off_a_code_card_is_denied_without_asking_the_judge(env, tool_input):
    out = gate.decide({"tool_name": CREATE, "tool_input": tool_input})
    assert decision(out) == "deny"
    assert "only a code card" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert calls(env) == []


def test_a_cloze_in_an_update_is_denied_too(env):
    out = gate.decide({"tool_name": UPDATE, "tool_input": {"cardId": "c1", "front": "A {{c1::b}}."}})
    assert decision(out) == "deny"
    assert calls(env) == []


def test_a_code_cards_own_blanks_are_not_a_flaw(env):
    exercise = {"kind": "fill", "brief": "Do it.", "source": "x = {{c1::2}}", "explain": "Why.",
                "cases": [{"expr": "x", "goal": "2"}]}
    assert gate.decide({"tool_name": "mcp__flashcard-mcp__create_code_card", "tool_input": {"exercise": exercise}}) is None


def test_the_rubric_names_every_issue_the_schema_allows():
    rubric = gate.RUBRIC.read_text()
    for issue in gate.ISSUES:
        assert f"`{issue}`" in rubric


def test_a_verdict_is_kept_for_the_same_text_and_no_other(env):
    gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is X?", "back": "Y."}})
    gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is X?", "back": "Y."}})
    assert len(calls(env)) == 1, "the same card asks the judge once"
    gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is X?", "back": "Z."}})
    assert len(calls(env)) == 2


def test_a_failed_judge_is_not_kept(env):
    for _ in range(2):
        assert decision(gate.decide({"tool_name": CREATE, "tool_input": {"front": "crash", "back": "x"}})) == "deny"
    assert len(calls(env)) == 2


def test_a_code_cards_explain_is_feedback_not_an_extra_on_its_back():
    out = {"asked": ["one idea"], "claims": [{"text": "why", "role": "step"}, {"text": "the wrong answer", "role": "extra"}], "issues": []}
    assert gate.verdict(out, code=True) == []
    assert gate.verdict(out)[0]["issue"] == "extra_info", "a plain card's back is still held to it"


def test_a_code_card_still_fails_for_asking_two_things_or_a_wrong_explain():
    out = {"asked": ["a", "b"], "claims": [], "issues": [{"issue": "incorrect", "detail": "No."}]}
    assert [i["issue"] for i in gate.verdict(out, code=True)] == ["not_atomic", "incorrect"]


def test_a_code_card_written_through_the_gate_is_not_refused_for_its_explain(env):
    exercise = {"kind": "predict", "brief": "What is it?", "source": "x = 1", "explain": "An RFC says so.",
                "cases": [{"expr": "x", "goal": "1"}]}
    assert gate.decide({"tool_name": "mcp__flashcard-mcp__create_code_card", "tool_input": {"exercise": exercise}}) is None


# ---- a judge with nothing to say is no pass -------------------------------------------
@pytest.mark.parametrize("front", ["no verdict", "retries"])
def test_an_empty_answer_denies_and_is_not_kept(env, front):
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": front, "back": "x"}})
    assert decision(out) == "deny"
    assert "could not judge" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert not any(gate.cache_dir().glob("*.json")) if gate.cache_dir().exists() else True


def test_an_empty_verdict_kept_from_before_is_asked_again(env):
    card = {"front": "Which header?", "back": "ETag"}
    kept = gate.cache_path(gate.judge_prompt(card))
    kept.parent.mkdir(parents=True)
    kept.write_text("{}")
    assert gate.run_judge(card)["asked"] == ["one thing"]
    assert len(calls(env)) == 1


def test_a_judge_that_times_out_denies_without_the_rubric_in_the_reason(env, monkeypatch):
    def too_slow(argv, **_):
        raise gate.subprocess.TimeoutExpired(argv, gate.TIMEOUT)

    monkeypatch.setattr(gate.subprocess, "run", too_slow)
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": "Q?", "back": "A"}})
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert decision(out) == "deny" and "took over" in reason and len(reason) < 300


def test_an_issue_of_the_wrong_shape_denies_rather_than_crashes_the_hook(env, monkeypatch):
    monkeypatch.setattr(gate, "run_judge", lambda card: {"asked": [], "claims": [], "issues": [{"issue": "incorrect"}]})
    assert decision(gate.decide({"tool_name": CREATE, "tool_input": {"front": "Q?", "back": "A"}})) == "deny"


# ---- the hook itself, as Claude Code runs it --------------------------------------------
def hook(event, env_vars):
    return subprocess.run([str(ROOT / "scripts" / "card-quality-gate")], input=event, capture_output=True, text=True,
                          env={**os.environ, **env_vars})


def test_the_hook_denies_over_stdin_and_passes_what_is_not_a_card_write(env):
    event = {"tool_name": CREATE, "tool_input": {"front": "What is it and how do you stop it?", "back": "x"}}
    p = hook(json.dumps(event), {})
    assert p.returncode == 0 and decision(json.loads(p.stdout)) == "deny"
    for other in ("not json", "[1, 2]", json.dumps({"tool_name": "Read"})):
        p = hook(other, {})
        assert (p.returncode, p.stdout) == (0, "")


def test_judging_a_stored_card_names_the_parts_a_split_cut_short_left(env, capsys, monkeypatch):
    monkeypatch.setattr(gate.sys, "argv", ["card-quality-gate", "--judge", "c1"])
    gate.main()
    assert json.loads(capsys.readouterr().out)["parts"] == ["A part"]
