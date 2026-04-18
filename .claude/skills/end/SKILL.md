---
name: end
description: "End a work block or close the day. Block-end: quick reflection to empty your head before a pause. Day-end: full review of activity, todos, and intentions. Trigger keywords: end, wrap up, close day, done for today, EOD, done with this block."
user_invocable: true
---

# /end — Closing Ritual

Interactive reflection that closes either a **work block** or the **full day**. Adapts automatically based on context.

- **Block-end**: Quick reflection to empty open thoughts before a micro pause. Captures what's unfinished, what's resolved, and any loose threads — so the developer can actually let go and pause.
- **Day-end**: Full review of git activity, session logs, todo updates, and intentions for next time.

## Core Guarantee

The developer leaves with their head empty: open loops captured, focus released, ready for either a pause or the next day. The reflection is grounded in evidence (git history, session logs), not just memory.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- One topic per message, with a few intentional pairings noted below. Pause for the developer's response.
- Ground the conversation in what actually happened — show the evidence first, then discuss.
- Keep it light. End of day is not the time for deep coaching.

## Invocation

```
/end        — Auto-detect: block-end if a kickoff is still open (no End logged after it), day-end otherwise
/end block  — Force block-end mode
/end day    — Force day-end mode
```

---

## Flow

### Phase 0: Detect Mode

Read today's `logs/YYYY-MM-DD.md`. Look at the session headers.

- If the most recent Kickoff/Refocus session has no matching End session after it → **block-end** (the developer is closing the block they started).
- If all Kickoff sessions have matching End sessions, or the developer passed `day` → **day-end**.
- The developer can always override with `block` or `day`.

**If block-end → jump to Block-End Flow below.**
**If day-end → continue to Phase 1.**

---

## Block-End Flow

A lightweight reflection to empty the developer's head before a pause. 3 questions, a short log entry, done.

### B1: Quick Summary

Show what happened in this block (from the most recent Kickoff/Refocus entry):

> **This block:** [focus from kickoff], [time frame]
> [Brief: what sessions ran, cards reviewed, wiki updates, commits — whatever is in the log since the kickoff]

### B2: Open Thoughts

Ask the head-emptying pair in one message, then the optional check-in:

1. **Anything still on your mind from this block, or anything to capture before you step away?** — unfinished thoughts, loose threads, quick todo additions, notes you don't want to forget. The point is to get it out of your head so you can actually pause.
2. **How did this block go?** (optional — "fine" or "skip" is fine)

### B3: Todo Touch-Up (if needed)

If the developer mentioned new items or completions in B2, update `todo.md` with confirmation.

### B4: Block Log

Append to `logs/YYYY-MM-DD.md`:

```markdown
## Session N — Block End (HH:MM)
- **Block focus:** [what was set in kickoff]
- **Achieved:** [brief — what actually happened]
- **Open threads:** [anything the developer emptied from their head]
- **Todo updates:** [if any]
```

### B5: Release

Brief sign-off that names the pause they planned:

> Block done. [Pause activity from kickoff] time. Go.

---

## Day-End Flow

### Phase 1: Evidence Gathering

Gather the day's activity silently (do not dump raw output). Read in parallel:

1. **Today's session log** (`logs/YYYY-MM-DD.md`) — what sessions were logged
2. **Todo file** (`todo.md`) — current state of the ordered list
3. **Git activity** — run `git log --oneline --since="8 hours ago" --author="$(git config user.name)"` and `git diff --stat HEAD~5` (adjust range based on commit count). Summarize: number of commits, key changes, files touched.

### Phase 2: Review & Reflection

Present a brief summary, then guide reflection one question at a time.

**Summary:**

> **Today's activity:**
> - [N] sessions logged (kickoff, refocus, study, etc.)
> - [N] commits: [brief summary of key changes]
> - [N] cards studied, [accuracy]% accuracy (if any study sessions)
> - [N] wiki pages created/updated (if any)
>
> **Top of todo list:**
> 1. [top item]
> 2. [second]
> 3. [third]

Then ask reflection questions, using the paired messages below:

1. **What did you achieve today, and how did today go compared to what you intended?** (developer's perspective — may differ from the evidence, and that's fine. "Fine" or "skip" on the reflection half is respected.)
2. **Anything to check off, add, or reorder in the todo list?**
3. **What carries forward to next time, and where did you leave off?** — anything that should bubble to the top for tomorrow, plus concrete unfinished threads or half-done ideas. The "left off" part becomes the re-entry point for the next kickoff.

### Phase 3: Freeform Reflection (optional)

If the developer wants to talk more, make space. If they're done, move to logging.

**Ending conditions:**
- Developer says "done", "that's it", or equivalent
- Conversation reaches natural resolution
- Developer always has final say

### Phase 4: Clean Commit

Check `git status` for any uncommitted changes. If there are:

1. Show a brief summary: files modified, added, deleted
2. Ask: "Want to commit these before we wrap up?"
3. If yes — stage changes, ask for a commit message (or offer to generate one from the diff), commit
4. If no — note it in the log as uncommitted carry-forward

If the working directory is clean, skip silently.

### Phase 5: Todo Update

Based on the reflection, update `todo.md`:
- Check off completed items (`- [x]`)
- Add new carry-forward items (position per developer's instruction, default to end)
- Reorder if requested — especially if something needs to bubble to the top for tomorrow
- Remove items the developer explicitly drops

Read `todo.md` before editing to work from current state.

### Phase 6: Session Log

Append to `logs/YYYY-MM-DD.md`.

```markdown
## Session N — End (HH:MM)
- **Achieved:** [what the developer said they accomplished]
- **Commits:** [count and brief summary of key changes]
- **Study stats:** [cards reviewed, accuracy, wiki pages — only if any]
- **Carry forward:** [items moving to next day, top priority called out]
- **Left off:** [unfinished threads to pick up tomorrow — where you left off, half-done ideas]
- **Reflection:** [1-2 sentence summary of how the day went]
- **Todo updates:** [items checked off, added, reordered, or removed]
```

Omit `Study stats` if the day had no study activity.

### Phase 7: Closing

Brief, warm sign-off. Don't over-summarize — the log has the details.

> Good day. [one sentence acknowledgment]. See you next time.

---

## Guardrails

**Always:**
- Check git activity for concrete evidence
- Read today's log for session context
- Update `todo.md`
- Write the session log
- Respect "done" / "skip" immediately

**Never:**
- Dump raw git log output — summarize it
- Force reflection if the developer wants to wrap up quickly
- Judge the day as good or bad — reflect what the developer says
- Add todos the developer didn't mention
- Silently reorder `todo.md` — always with confirmation
- Over-summarize — the developer was there, they know what happened
