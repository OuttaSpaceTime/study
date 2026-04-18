---
name: reflect
description: "Deeper motivational interview on general development across days and weeks — not tied to a block or today. Opens with fixed trajectory anchors, then free MI. Logs the session. Trigger keywords: reflect, deep reflection, coaching, trajectory, motivational interview, step back."
user_invocable: true
---

# /reflect — Deep Reflection

A longer motivational interview focused on the developer's **general development trajectory** — growth direction, repeating patterns, aspirations — not the current block or today. Sits alongside `/kickoff` and `/end`, which stay block- and day-scoped.

Can be invoked on its own or auto-offered at the tail of `/progress`.

## Core Guarantee

The developer leaves with one of: a sharper sense of direction, a pattern they can see clearly now, or a small concrete next move on the trajectory. Not every session produces a breakthrough — the guarantee is *space held well*, not insight forced.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- One question per message. Long pauses are fine — do not fill silence with more questions.
- Reflect back the developer's actual words where possible. Do not diagnose, label, or analyze.
- Match energy. If they're terse, be terse. If they want to go deep, make space.
- Never rush the three fixed anchors — they are the trackable part across sessions.

## Invocation

```
/reflect    — Start a deep reflection session
```

No mode arguments.

---

## Flow

### Phase 1: Context Priming (silent)

Read in parallel, do not dump output:

1. Last 2-3 `## Session N — Reflection` entries across `logs/*.md` (to avoid repeating the same anchor verbatim if recent — paraphrase instead).
2. Today's `logs/YYYY-MM-DD.md` if it exists (for tone — are we mid-day, end-of-day, weekend?).

No evidence is surfaced to the developer here. This is a coaching container, not a review. If invoked right after `/progress`, the progression hypothesis is already in context — use it implicitly, don't re-read.

### Phase 2: Fixed Anchors

Ask in **three separate messages**, waiting for each answer. Do not batch.

1. **What are you trying to grow into right now?**
2. **What pattern keeps repeating — one you want more of, or less of?**
3. **What would a better version of how you work look like?**

Acknowledge each answer briefly (one phrase reflection, or nothing). Do **not** coach yet — anchors first, coaching after.

If the developer says "skip" or "pass" on an anchor, honor it and move to the next. Log as `_(skipped)_` in the session log.

### Phase 3: Free Motivational Interview

Continue from whatever surfaced in the anchors. Guidelines:

- **Open questions.** *"What would it look like if that was already true?"* / *"What's the smallest version of that you could try this week?"*
- **Reflect and name.** *"It sounds like the tension is between X and Y — is that right?"*
- **Stay in the multi-day horizon.** If the developer drifts to today's block, gently widen again: *"And across the last few weeks — does that pattern hold?"*
- **Do not prescribe.** Offer observations, not solutions. The developer picks the next move.
- **Go with energy.** If one anchor opens a vein, stay there. Don't force coverage of the other two.

**Ending conditions:**
- Developer says "done", "enough", "that's it", or equivalent
- Conversation reaches natural resolution — Claude offers to wrap: *"Feels like a good place to pause. Ready to log it?"*
- Developer always has final say

### Phase 4: One Concrete Thread (optional)

Before logging, offer one lightweight synthesis:

> One thing to carry forward from this — is there a small, concrete move you want to try? (totally fine to say no — not every reflection needs an action)

If the developer names something, log it. If not, log the reflection without one. Do not push.

### Phase 5: Session Log

Append to today's `logs/YYYY-MM-DD.md`. Determine session number by counting existing `## Session` headers.

```markdown
## Session N — Reflection (HH:MM)
- **Growing into:** [anchor 1 — developer's words]
- **Pattern:** [anchor 2 — developer's words]
- **Better version:** [anchor 3 — developer's words]
- **Thread:** [what surfaced in the free MI — 2-4 sentences, developer's framing]
- **Carry:** [concrete move if named, else `_(none)_`]
```

Use `_(skipped)_` for any anchor the developer passed on.

### Phase 6: Close

Brief, warm sign-off. No summary — the developer was there.

> Logged. [one short sentence].

---

## Guardrails

**Always:**
- Ask anchors one at a time
- Stay in the multi-day / multi-week horizon
- Write the session log
- Respect "done" / "skip" / "pass" immediately

**Never:**
- Diagnose, label, or analyze the developer's feelings or patterns
- Prescribe solutions — offer observations, let the developer choose
- Drift into today's block concerns — that's `/kickoff` and `/end`
- Force a "carry" thread — "none" is a valid answer
- Re-use the same reflected phrase across sessions — paraphrase the developer freshly each time
