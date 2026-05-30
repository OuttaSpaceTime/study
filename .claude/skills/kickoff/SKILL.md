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

Read today's `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder; create it with a `# <YYYY-MM-DD>` header if it doesn't exist). Count existing `## Session N — Kickoff` headers.

- **Zero** → this is the **first kickoff** of the day. Run full cadence.
- **One or more** → this is a **refocus**. Run delta cadence (skips Feeling + Noticing).

**First kickoff only:** also read yesterday's log (`logs/<MM>/<YYYY-MM-DD>.md` for the previous day — derive `<MM>` from yesterday's date, which may be a different month folder than today's) and look for a `**Left off:**` field in the last `## Session N — End` entry. If found, surface it at the top of Phase 2 as a re-entry hint:

> **Yesterday you left off:** [left off text]

### Phase 2: Todo Read (silent)

Read `todo.md` from the project root. It has two headings: `## Today` (today's chosen tasks, cleared daily) and `## Backlog` (the ongoing ordered list). Top item of `## Today` is the current highest priority when populated; otherwise top of `## Backlog` is. Do **not** present the list to the developer — the todo list is auto-managed. Hold it in memory for Phase 2.5 and Phase 3.5 logic.

If `todo.md` doesn't exist, create it with both headings empty:

```markdown
# Todo

## Today

## Backlog

```

### Phase 2.5: Stale Today Clear (first kickoff only)

If this is the first kickoff of the day **and** `## Today` has items, it's from a previous day. Auto-migrate without prompting:

- Unchecked items (`- [ ]`) → move to the top of `## Backlog`, preserving order
- Checked items (`- [x]`) → drop

Leave `## Today` empty. The developer provides a fresh list in Phase 2.8.

On a refocus (not the first kickoff), skip this phase — leave `## Today` as-is.

### Phase 2.8: Today's List (first kickoff only)

Ask as one paired message:

> **What are your tasks for today, and how do you want to reward yourself with pauses?**

Wait for the developer's response. Expect a list of tasks and a description of pauses (could be one line each, could be a bulleted list).

Write the tasks to `## Today` in `todo.md` as `- [ ]` items, preserving the order given. Do **not** put pauses in `todo.md` — they go into the session log's **Pauses:** field in Phase 5.

If the developer gives only tasks and no pauses (or vice versa), accept what they gave — don't re-prompt for the missing half. Note the absence in the log.

On a refocus, skip this phase entirely.

### Phase 3: Fixed Questions

Ask in two paired messages, waiting for each answer.

**First kickoff of the day (full cadence):**

1. **How are you feeling today, and what have you been noticing lately?** (patterns, friction, things on your mind)
2. **What do you want to focus on, and what's blocking you or causing friction?**

**Refocus (delta cadence) — skip the feeling/noticing pair:**

1. **What's your focus for this next block, and anything in the way?**

Keep your responses brief — acknowledge, maybe reflect back one phrase, move on. Don't coach yet.

### Phase 3.5: Todo Reorder (conditional)

Compare the stated focus to `## Today` first, then `## Backlog`. Reorder happens within `## Today` — the focus should be at the top of `## Today`.

- **If the focus matches an item already at the top of `## Today`** → acknowledge briefly ("top of the list, good") and move on.
- **If the focus matches an item lower in `## Today`** → propose: *"You said X is your focus — want me to move it to the top of Today?"* Apply on confirm.
- **If the focus matches an item in `## Backlog`** → propose: *"Want me to pull '[item]' up to the top of Today?"* Apply on confirm (move, don't copy).
- **If the focus is entirely new** → propose: *"Want me to add '[focus]' to the top of Today?"* Apply on confirm.
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

Append to `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder). Determine the session number by counting existing `## Session` headers in today's log.

**First kickoff of the day:**

```markdown
## Session N — Kickoff (HH:MM)
- **Today's tasks:** [the list the developer gave for `## Today`]
- **Pauses:** [how the developer wants to reward themselves with pauses today]
- **Feeling:** [brief]
- **Noticing:** [brief]
- **Focus:** [stated focus]
- **Time:** [time frame set in the interview]
- **Next:** [what the developer will move to when time is up]
- **Pause:** [what the developer will do in the micro pause between this block and the next]
- **Blockers:** [what's in the way]
- **Todo updates:** [items added / checked off / reordered, including carry-overs from prior `## Today` to `## Backlog`]
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
- Ask questions one at a time (the Today-tasks + pauses pair is one message)
- Read `todo.md` every session silently; only modify with explicit confirmation except for the automated stale-`## Today` clear, and never present the list unprompted
- On the first kickoff of the day, auto-clear stale `## Today` (unchecked → Backlog, checked → dropped) and ask for today's tasks + pauses before the fixed questions
- Open the motivational interview with time-framing
- Write the session log
- Respect "done" / "stop" immediately

**Never:**
- Skip the fixed questions on a first kickoff (they're the trackable part)
- Ask for today's tasks on a refocus — that's first-kickoff only
- Silently reorder `todo.md` beyond the automated stale-`## Today` clear — always propose, wait for confirmation
- Over-coach — if the developer is clear and ready, let them go
- Create todos the developer didn't mention
- Judge or diagnose feelings — reflect, don't analyze
- Collapse the motivational interview to just time-framing — always leave room for full coaching
