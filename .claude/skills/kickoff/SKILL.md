---
name: kickoff
description: "Daily ritual to start or refocus a session. Fixed check-in questions, freeform motivational interview, todo review and reorder, session logging. Trigger keywords: kickoff, start day, morning, begin, ritual, refocus."
user_invocable: true
---

# /kickoff — Focus Ritual

Interactive check-in that opens a session or refocuses mid-day. Starts with fixed daily questions (trackable across days), reorders the todo list around the stated focus, then flows into a freeform motivational interview to set boundaries and get unstuck.

Designed to be run **once for a broad vision** or **several times a day as a quick refocus** — the flow adapts automatically.

## Core Guarantee

The developer leaves kickoff with: (1) a clear top-of-list focus, (2) a time frame and realistic expectations for this block, (3) any blockers surfaced, (4) momentum to start. Some days it's two minutes. Other days it's a longer coaching session to work through friction.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- One question or topic per message, with a few intentional pairings noted below. Pause for the developer's response.
- Never rush the fixed questions — each one matters, even when paired.
- Match the developer's energy. If they're brief, be brief. If they want to talk, make space.

## Invocation

```
/kickoff    — Start (or refocus, if already a kickoff today)
```

No mode arguments. The flow adapts to whether it's the first kickoff of the day (full cadence) or a subsequent refocus (delta cadence).

---

## Flow

### Phase 1: Detect Session Type

Read today's `logs/YYYY-MM-DD.md` (create date if file doesn't exist). Count existing `## Session N — Kickoff` headers.

- **Zero** → this is the **first kickoff** of the day. Run full cadence.
- **One or more** → this is a **refocus**. Run delta cadence (skips Feeling + Noticing).

**First kickoff only:** also read yesterday's log (`logs/YYYY-MM-DD.md` for the previous day) and look for a `**Left off:**` field in the last `## Session N — End` entry. If found, surface it at the top of Phase 2 as a re-entry hint:

> **Yesterday you left off:** [left off text]

### Phase 2: Todo Read (silent)

Read `todo.md` from the project root. It is a single ordered list — top item is the current highest priority. Do **not** present the list to the developer — the todo list is auto-managed. Hold it in memory for Phase 3.5 reorder logic.

If `todo.md` doesn't exist, create it empty:

```markdown
# Todo

```

Move directly into Phase 3 without surfacing the current items or asking for check-offs.

### Phase 3: Fixed Questions

Ask in two paired messages, waiting for each answer.

**First kickoff of the day (full cadence):**

1. **How are you feeling today, and what have you been noticing lately?** (patterns, friction, things on your mind)
2. **What do you want to focus on, and what's blocking you or causing friction?**

**Refocus (delta cadence) — skip the feeling/noticing pair:**

1. **What's your focus for this next block, and anything in the way?**

Keep your responses brief — acknowledge, maybe reflect back one phrase, move on. Don't coach yet.

### Phase 3.5: Todo Reorder (conditional)

Compare the stated focus to the current top of `todo.md`.

- **If the focus matches an existing item that is already at the top** → acknowledge briefly ("top of the list, good") and move on.
- **If the focus matches an existing item lower down** → propose: *"You said X is your focus — want me to move it to the top?"* Apply on confirm.
- **If the focus is new (not yet on the list)** → propose: *"Want me to add '[focus]' to the top of your list?"* Apply on confirm.
- **If unsure which item the focus maps to** → ask the developer to pick, don't guess.

Only touch `todo.md` with the developer's explicit confirmation.

### Phase 4: Motivational Interview

Always **open with time-framing**, then continue into full coaching. Do not collapse the interview to just the time question — time-framing is the opener, not the whole thing.

**Opener (always):**

> How much time do you have for this block, and what feels realistic in that window?

Wait for response. If the developer's answer reveals the stated focus is too ambitious for the time they have, gently name it and help them scope down.

**Then ask the boundary pair (always, in one message):**

> When the time is up, what's the next thing you'll move to — and what do you want to do in your micro pause before that?

This creates a hard boundary (no drift into sidetracks) and names the pause as a deliberate practice. Help the developer name something concrete for the pause (stretch, breathe, step outside, make tea, close eyes for two minutes). Log the answers as **Next:** and **Pause:** in the session log.

**Then continue coaching.** Start from whatever surfaced in the fixed questions — blockers, feelings, friction — and keep going until the developer is ready to start.

**Guidelines:**

- Use open questions: *"What would it look like if that blocker was resolved?"* / *"What's the smallest step you could take on that?"*
- Reflect back what you hear — *"It sounds like the real friction is X, not Y"*
- Help set concrete boundaries — *"Given you have 90 minutes, what's the one thing that matters most?"*
- If the developer is already energized, keep it short — don't force depth
- If they're stuck or low-energy, spend more time here — help them find one concrete thing to start with

**Ending conditions:**

- The developer says "done", "let's go", "stop", or equivalent
- The conversation reaches natural resolution — Claude suggests wrapping: *"Sounds like you've got clarity. Ready to start?"*
- The developer always has the final say

### Phase 5: Session Log

Append to `logs/YYYY-MM-DD.md`. Determine the session number by counting existing `## Session` headers in today's log.

**First kickoff of the day:**

```markdown
## Session N — Kickoff (HH:MM)
- **Feeling:** [brief]
- **Noticing:** [brief]
- **Focus:** [stated focus]
- **Time:** [time frame set in the interview]
- **Next:** [what the developer will move to when time is up]
- **Pause:** [what the developer will do in the micro pause between this block and the next]
- **Blockers:** [what's in the way]
- **Todo updates:** [items added / checked off / reordered]
- **Interview notes:** [2-3 sentence summary — what shifted, what became clear]
```

**Refocus (delta cadence):**

```markdown
## Session N — Kickoff/Refocus (HH:MM)
- **Focus:** [stated focus]
- **Time:** [time frame set in the interview]
- **Next:** [what the developer will move to when time is up]
- **Pause:** [what the developer will do in the micro pause between this block and the next]
- **Blockers:** [what's in the way]
- **Todo updates:** [items added / checked off / reordered]
- **Interview notes:** [1-2 sentence summary]
```

**Log content guidelines:**
- Capture the developer's actual words where possible, not your interpretation
- Interview notes reflect what shifted or became clear, not a transcript
- One line per field when possible

### Phase 6: Handoff

After logging, briefly confirm the focus and time frame:

> You're set. Next [time]: [focus]. Go.

If the stated focus maps to existing wiki pages or flashcards (learning-flavored focus), offer to chain:

> This looks like a learning block. Want to kick off `/study` or `/study-walkthrough`?

Otherwise hand off plainly. Don't force the suggestion.

---

## Guardrails

**Always:**
- Ask questions one at a time
- Read `todo.md` every session silently; only modify with explicit confirmation and never present the list unprompted
- Open the motivational interview with time-framing
- Write the session log
- Respect "done" / "stop" immediately

**Never:**
- Skip the fixed questions on a first kickoff (they're the trackable part)
- Silently reorder `todo.md` — always propose, wait for confirmation
- Over-coach — if the developer is clear and ready, let them go
- Create todos the developer didn't mention
- Judge or diagnose feelings — reflect, don't analyze
- Collapse the motivational interview to just time-framing — always leave room for full coaching
