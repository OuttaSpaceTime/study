"""The card-quality gate: no flawed card is written to the deck. `scripts/card-quality-gate` is the hook.

On every flashcard-mcp `create_card` and `update_card` in this repo (`.claude/settings.json`), the
card as it would be saved is judged against `.claude/skills/references/card-quality.md` by
`claude -p` (Opus, on the Claude subscription: no API key is passed on). A flawed card is
denied, with the issues as the reason, so the session revises it and writes again. A card is only
judged on what a write changes: an `update_card` that touches neither front nor back (tags, a
deck move) passes unjudged, and one that changes one side is judged with the other side read from
the deck.

It replaced the Omvida grader's per-review card check (2026-10-31): a flaw caught at write time
never reaches a review. A gate in the skills (a reviewer subagent each skill must call) was the
alternative, and rejected: a skill that forgot it would let the card through, while a hook holds
for every session in the repo, the headless /study-card-check included. One inside flashcard-mcp
was rejected too: an LLM call in the deck server would slow every write, the app's included.

The judge counts before it judges (2026-11-03): what the front asks, and each claim of the back, with
the verdict on atomicity computed here from those counts. Asked only for a list of flaws, Sonnet let
through 8 of 26 multi-part cards and 19 of 32 padded ones on labelled cards from the deck,
"Name 3+ vectors" included; `tests/card-quality/` keeps that benchmark (`scripts/card-quality-eval`). The counts come back with
a refusal, so the session sees what to split. `--judge <card id>` prints the same verdict for a stored
card: /study-card-check judges with it, so the check and the gate cannot disagree.

A verdict is kept (`CACHE`), keyed on the card's sides, the rubric, the prompt and the model: judging the same
text again says the same, and a sweep over the deck (`scripts/card-check-sweep`) can then be stopped and resumed for
nothing. Any change to the rubric invalidates all of them, which is what it should do.

Fails closed: a judge that cannot run denies the write with the reason, since letting it through
is what the gate exists to stop. Malformed hook input passes (there is no card to judge).
`CARD_QUALITY_CLAUDE` names the claude to run (the tests' fake).
"""
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.config import master_db

ROOT = Path(__file__).resolve().parent.parent

RUBRIC = ROOT / ".claude" / "skills" / "references" / "card-quality.md"
CLOZE = re.compile(r"\{\{c\d+::")
TOOLS = {"mcp__flashcard-mcp__create_card", "mcp__flashcard-mcp__update_card",
         "mcp__flashcard-mcp__create_code_card", "mcp__flashcard-mcp__update_code_card"}
# What the judge names itself. `not_atomic` and `extra_info` it does not: they are computed from its counts.
ISSUES = ["incorrect", "too_vague", "ambiguous_front", "opinion_bait", "yes_no", "mismatched", "outdated",
          "gives_away", "tests_spelling", "padded_code", "fragile"]
SCHEMA = {
    "type": "object",
    "properties": {
        "asked": {
            "type": "array",
            "description": "One entry per thing to retrieve; a selection list gets one entry per member",
            "items": {"type": "string"},
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "role": {"type": "string", "enum": ["answer", "step", "extra"]}},
                "required": ["text", "role"],
                "additionalProperties": False,
            },
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"issue": {"type": "string", "enum": ISSUES}, "detail": {"type": "string"}},
                "required": ["issue", "detail"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["asked", "claims", "issues"],
    "additionalProperties": False,
}
JUDGE = """You are the quality gate for a software developer's spaced-repetition deck. You get one
flashcard about to be saved: its front (the question) and back (the answer), as simple HTML; read
them as the text they render to. A code card's front is its exercise, as the rubric describes.
First count, as the rubric's "Count first" says: fill in `asked` and `claims`. Those two decide atomicity
on their own, so be exact, and do not repeat them as issues. Then list any other flaw from the rubric's
tables with a one-sentence detail saying what is wrong and how to fix it. Only clear flaws there.

"""
# Opus at high effort, against Sonnet low, on the held-out half of the benchmark, each card twice: it caught all
# 32 padded backs (Sonnet 30) and 24 of 26 multi-part cards (23), refused no sound card of 48 (Sonnet 7), and never
# changed its mind (Sonnet on 4 cards of 58). A write is rare and a wrong verdict rewrites a card, so it is worth it.
MODEL = "opus"
EFFORT = "high"
TIMEOUT = 120


def query_deck(sql, *args):
    db = sqlite3.connect(f"file:{master_db()}?mode=ro", uri=True)
    try:
        return db.execute(sql, args).fetchall()
    finally:
        db.close()


def stored_card(card_id):
    rows = query_deck("SELECT front, back, exercise FROM Card WHERE id = ?", card_id)
    if not rows:
        raise LookupError(f"no card {card_id} in the deck")
    return {"front": rows[0][0], "back": rows[0][1], "exercise": rows[0][2]}


def stored_parts(card_id):
    """The fronts of the cards made from this one: a split cut short leaves them beside the original."""
    return [row[0] for row in query_deck("SELECT front FROM Card WHERE inheritedFrom = ?", card_id)]


def subject(card):
    """What the judge reads of a card in the deck: a code card is its exercise."""
    return code_card_to_judge(json.loads(card["exercise"])) if card.get("exercise") else card


def judge_stored(card_id):
    """--judge: the gate's verdict on a card in the deck, for /study-card-check."""
    card = subject(stored_card(card_id))
    out = run_judge(card)
    issues = verdict(out, bool(card.get("code")))
    return {"passes": not issues, "asked": out["asked"], "claims": out["claims"], "issues": issues,
            "parts": stored_parts(card_id)}


def code_card_to_judge(exercise):
    """A code card, as what it asks and what it teaches. flashcard-mcp has already run it, so whether
    its goals are true is not in question here; whether it is a good question is."""
    # A prediction's goals are what it asks, so they reach the judge as hidden as they reach the
    # developer, or every one of them would read as giving its answer away.
    hide = exercise.get("kind") == "predict"
    cases = "\n".join(f"{c['expr']}  # => " + (f"{{{{c1::{c['goal']}}}}}" if hide else c["goal"])
                      for c in exercise.get("cases", []))
    return {"front": f"Code card, kind {exercise.get('kind', '?')}: {exercise.get('brief', '')}\n"
                     f"<pre>{exercise.get('source', '')}\n{cases}</pre>",
            "back": exercise.get("explain", ""), "code": True}


def card_to_judge(tool, tin):
    """The card as the write would leave it, or None when there is nothing to judge: an update that
    changes neither side (tags, a deck move, or the sides as they are stored)."""
    if tool.endswith("code_card"):
        return code_card_to_judge(tin.get("exercise") or {})
    if tool.endswith("create_card"):
        return {"front": tin.get("front") or "", "back": tin.get("back") or ""}
    if "front" not in tin and "back" not in tin:
        return None
    stored = stored_card(tin["cardId"])
    card = dict(stored, **{k: tin[k] for k in ("front", "back") if k in tin})
    return None if card == stored else card


def cache_dir():
    return Path(os.environ.get("CARD_QUALITY_CACHE") or Path.home() / ".cache" / "study-card-quality" / "verdicts")


def cache_path(prompt):
    key = "\0".join([MODEL, EFFORT, JUDGE, RUBRIC.read_text(), prompt])
    return cache_dir() / (hashlib.sha256(key.encode()).hexdigest() + ".json")


def judge_prompt(card):
    return f"<front>\n{card['front']}\n</front>\n<back>\n{card['back']}\n</back>"


def complete(out):
    """A verdict says all three things. Anything less is no verdict, and an empty one would read as sound."""
    return isinstance(out, dict) and all(isinstance(out.get(k), list) for k in ("asked", "claims", "issues"))


def run_judge(card):
    """What the judge said of a card: its `asked`, `claims` and `issues`."""
    prompt = judge_prompt(card)
    kept = cache_path(prompt)
    if kept.exists():
        out = json.loads(kept.read_text())
        if complete(out):
            return out
    out = ask_judge(prompt)
    kept.parent.mkdir(parents=True, exist_ok=True)
    temporary = kept.with_suffix(f".{os.getpid()}.tmp")  # several judges run at once: never a half-written verdict
    temporary.write_text(json.dumps(out))
    temporary.replace(kept)
    return out


def ask_judge(prompt):
    argv = [os.environ.get("CARD_QUALITY_CLAUDE", "claude"), "-p", prompt, "--model", MODEL,
            "--effort", EFFORT, "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
            "--system-prompt", JUDGE + RUBRIC.read_text(), "--tools", "", "--strict-mcp-config",
            "--setting-sources", "", "--no-session-persistence"]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    with tempfile.TemporaryDirectory() as cwd:
        try:
            p = subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            # Not the exception's own text: it spells out the argv, rubric and all, into the session's reason.
            raise RuntimeError(f"the judge took over {TIMEOUT} seconds") from None
    try:
        envelope = json.loads(p.stdout)
    except ValueError:
        raise RuntimeError((p.stderr.strip().splitlines() or [f"claude exited {p.returncode}"])[0]) from None
    if envelope.get("is_error") or envelope.get("subtype") != "success":
        raise RuntimeError(str(envelope.get("result") or envelope.get("subtype") or "claude failed"))
    out = envelope.get("structured_output")
    if not complete(out):
        raise RuntimeError("the judge gave no verdict")
    return out


def verdict(out, code=False):
    """The flaws, from the counts and the judge's own. The counts decide atomicity here, not the judge:
    it can count a card right and still decide to let it pass, which is the failure this exists to stop.

    A code card's `explain` is never counted as extra. Extra facts on a back are read during recall without being
    retrieved, but a code card is passed by running it, and `explain` comes afterwards, as the feedback that says why:
    naming the tempting wrong answer is its job. Counting it had the judge flag 3 of the deck's 5 code cards for exactly
    the sentences that teach (2026-11-04). It is still judged for being wrong or giving the answer away."""
    asked = out["asked"]
    extra = [] if code else [c.get("text", "") for c in out["claims"] if c.get("role") == "extra"]
    issues = []
    if len(asked) > 1:
        issues.append({"issue": "not_atomic",
                       "detail": f"It asks {len(asked)} things: {'; '.join(asked)}. Split it, one card per thing asked."})
    if extra:
        issues.append({"issue": "extra_info",
                       "detail": f"The back says more than the front asks: {'; '.join(extra)}. Take it out of this back; "
                                 "if it is worth keeping, give it a card of its own."})
    return issues + [i for i in out["issues"] if i.get("issue") in ISSUES]


def judge(card):
    return verdict(run_judge(card), bool(card.get("code")))


def deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def plain_cloze(tool, tin):
    """A cloze on a card that isn't a code card, which needs no judge to refuse: flashcard-mcp would
    too. A cloze hands over the sentence frame, so it tests recognition rather than retrieval."""
    if tool.endswith("code_card"):
        return False
    return any(CLOZE.search(str(tin.get(side) or "")) for side in ("front", "back"))


def refusal(tool, tin):
    """Why this write must not happen, or None."""
    if plain_cloze(tool, tin):
        return ("Card quality gate: cloze deletions are not allowed: only a code card has them "
                "(create_code_card, .claude/skills/references/code-cards.md). Ask a question instead.")
    card = card_to_judge(tool, tin)
    issues = judge(card) if card is not None else []
    if not issues:
        return None
    lines = "\n".join(f"- {i['issue']}: {i['detail']}" for i in issues)
    return ("Card quality gate: this card is not saved. Its flaws:\n" + lines + "\nRevise it per "
            ".claude/skills/references/card-quality.md (\"Fixing a flaw: keep the information\": "
            "split rather than drop an idea) and write again. If you think the gate is wrong: with "
            "the developer in the session, show them the card and these flaws and let them decide "
            "how to rephrase; unattended (claude -p), leave the card as it was and say why. Never "
            "resubmit it unchanged.")


def decide(event):
    tool = event.get("tool_name")
    if tool not in TOOLS:
        return None
    # Everything past this point, as a hook that raises exits 1, which Claude Code reads as "go ahead".
    try:
        reason = refusal(tool, event.get("tool_input") or {})
    except Exception as e:  # noqa: BLE001 (any failure denies, with what went wrong)
        reason = (f"Card quality gate could not judge this card ({e}). Try the write again; "
                  "if it keeps failing, tell the developer.")
    return deny(reason) if reason else None


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--judge":
        print(json.dumps(judge_stored(sys.argv[2]), indent=1))
        return
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return
    if not isinstance(event, dict):
        return
    out = decide(event)
    if out:
        print(json.dumps(out))
