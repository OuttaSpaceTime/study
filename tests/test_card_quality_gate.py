"""The card-quality gate (scripts/card-quality-gate), with a fake claude and a throwaway deck."""

import importlib.machinery
import importlib.util
import json
import sqlite3
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("card_quality_gate", str(ROOT / "scripts" / "card-quality-gate"))
spec = importlib.util.spec_from_loader("card_quality_gate", loader)
gate = importlib.util.module_from_spec(spec)
loader.exec_module(gate)

CREATE = "mcp__flashcard-mcp__create_card"
UPDATE = "mcp__flashcard-mcp__update_card"

# Flags "two_questions" when the front has " and how ", "incorrect" when the back says 200 OK,
# fails when the front says "crash"; records each prompt it was given.
FAKE = """#!/usr/bin/env python3
import json, os, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(json.dumps({"prompt": prompt, "argv": sys.argv[1:], "key": os.environ.get("ANTHROPIC_API_KEY")}) + "\\n")
if "crash" in prompt:
    print("boom", file=sys.stderr); sys.exit(1)
issues = []
if " and how " in prompt:
    issues.append({"issue": "two_questions", "detail": "Asks what and how."})
if "200 OK" in prompt:
    issues.append({"issue": "incorrect", "detail": "A matching ETag gets 304."})
print(json.dumps({"type": "result", "is_error": False, "structured_output": {"issues": issues}}))
"""


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake = tmp_path / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    db = tmp_path / "deck.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE Card (id TEXT PRIMARY KEY, front TEXT, back TEXT)")
    con.execute("INSERT INTO Card VALUES ('c1', 'Which header revalidates an ETag?', '<code>If-None-Match</code>.')")
    con.commit()
    con.close()
    log = tmp_path / "calls.jsonl"
    monkeypatch.setenv("CARD_QUALITY_CLAUDE", str(fake))
    monkeypatch.setenv("FLASHCARD_MASTER_DB", str(db))
    monkeypatch.setenv("FAKE_LOG", str(log))
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
    assert call["argv"][call["argv"].index("--model") + 1] == "sonnet"
    assert call["key"] is None, "the judge runs on the subscription, not the API key"


def test_a_flawed_card_is_denied_with_its_flaws(env):
    out = gate.decide({"tool_name": CREATE, "tool_input": {"front": "What is CSRF and how do you stop it?", "back": "x"}})
    assert decision(out) == "deny"
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "two_questions: Asks what and how." in reason
    assert "split rather than drop" in reason


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


def test_the_rubric_names_every_issue_the_schema_allows():
    rubric = gate.RUBRIC.read_text()
    for issue in gate.ISSUES:
        assert f"`{issue}`" in rubric
