---
title: Reflection & Progression Skills
status: implemented
created: 2026-04-17
---

## Outcome

Two skills created:
- `.claude/skills/reflect/SKILL.md` — `/reflect`
- `.claude/skills/progress/SKILL.md` — `/progress`

Decisions locked: names `/reflect` + `/progress`; progression window = since-last-progression with 14d fallback (overrides `7d`/`30d`); reflection = 3 fixed anchors then free MI; progression hypothesis = structured Growth/Drift/Tension; progression auto-offers `/reflect`. Evidence for `/progress` = commits + session logs + todo; wiki due-list explicitly excluded.

Still to do (not implemented): update `AGENTS.md` skill list to include the two new skills.


# Scout: Reflection & Progression Skills

## Request

Define two new interactive skills:

1. **Deep reflection / motivational interview** — a longer, MI-style coaching session distinct from the short coaching already embedded in `/kickoff` and `/end`.
2. **Progression check** — reads recent commits, logs, todo; asks a few calibrating questions; forms a hypothesis; gives feedback on the developer's trajectory; then suggests running the deep reflection skill.

Both log sessions. Both read recent commits + session logs.

## Problem Frame (CP1)

**Today:** `/kickoff` opens a session with fixed check-ins + a short motivational interview focused on *this block's* focus and boundaries. `/end` closes a block or day with reflection grounded in today's log/git. Neither steps back to ask "how is the developer *progressing* across days/weeks" or holds space for a longer MI unanchored to a specific block.

**After:** Two new entry points sit alongside kickoff/end. One ("progression") surveys the recent past (days, not just today), synthesizes a hypothesis, and delivers feedback. The other ("reflection") is a pure MI container for deeper work — invoked on its own, or suggested at the tail of a progression check.

**Framing (locked):** Both skills operate on the **multi-day / multi-week** horizon — "general development," not this block or today. Kickoff and end stay as they are; these two sit *alongside* for cross-day work.

- **Reflection** = deeper MI coaching on general development trajectory, ambitions, friction patterns. Not tied to a specific focus block.
- **Progression** = evidence-grounded trajectory check. Reads recent commits + logs across several days/weeks, asks calibrating questions, states a hypothesis, gives feedback, suggests reflection.

## Open Questions (blocking)

- Naming — `/reflect` + `/progress`? Other?
- Progression window — rolling 7 days? 14? Since last progression check (tracked how)?
- Reflection structure — fully open MI, or opens with a few fixed prompts?
- Chaining — does progression *auto-offer* reflection, or just mention it?

(Further checkpoints TBD after framing lock-in.)
