---
name: progress
description: "Cross-day/week progression check. Reads recent commits, session logs, and todo; asks calibrating questions; states a falsifiable hypothesis about trajectory (Growth/Drift/Tension); gives feedback; auto-offers /reflect. Trigger keywords: progress, progression, check in, trajectory, how am I doing, weekly review."
user_invocable: true
---

# /progress — Progression Check

An evidence-grounded trajectory check across the last several days or weeks. Reads recent commits, session logs, and the todo list; asks 2-3 calibrating questions; synthesizes a **falsifiable hypothesis** about the developer's trajectory that they can push back on; delivers feedback; then auto-offers `/reflect` to go deeper.

Distinct from `/end day` (which reflects on **today**) — `/progress` operates on the **multi-day horizon**.

## Core Guarantee

The developer leaves with a clearer picture of how they've actually been working over the window — not just vibes — and a decision point: go deeper now (`/reflect`), adjust, or carry on. The hypothesis is always *falsifiable and evidence-tied* — the developer must be able to disagree concretely.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- Evidence first, then questions, then hypothesis. Never open with the hypothesis.
- State claims with evidence — commit ranges, log excerpts, specific focuses named in kickoffs.
- Make the hypothesis easy to disagree with. Invite pushback explicitly.

## Invocation

```
/progress         — Since last /progress session; 14-day fallback if none found
/progress 7d      — Override window: last 7 days
/progress 30d     — Override window: last 30 days
```

---

## Flow

### Phase 1: Window Resolution

Determine the window:

1. Scan `logs/*/*.md` (latest first; logs are in zero-padded month folders) for a `## Session N — Progression` header. Parse its date from the filename.
2. If found → window = from that date through today.
3. If not found → window = last 14 days.
4. If the developer passed an override (`7d`, `30d`, etc.) → use that instead.

Note the resolved window — you will state it to the developer in Phase 3.

### Phase 2: Evidence Gathering (silent)

Read in parallel. Do **not** dump raw output.

1. **Commits in window:**
   ```
   git log --oneline --since="<window-start>" --author="$(git config user.name)"
   ```
   Note count, dominant themes (look at commit subjects), rhythm (consecutive days, gaps).

2. **Session logs in window:** glob `logs/*/*.md` (logs are grouped in zero-padded month folders, so the window may span several) and read every file whose `YYYY-MM-DD` filename date falls within the window. Extract:
   - Kickoff focuses and blockers
   - End-of-day `Left off:` and `Carry forward:`
   - Reflection entries (previous `## Session N — Reflection` if any)
   - Study activity (cards, accuracy, wiki pages)

3. **Current `todo.md`** — top items and total length. Cross-reference: do recent kickoff focuses match what's at the top?

Synthesize mentally. Do not write anything yet.

### Phase 3: Summary Presentation

Surface a tight, evidence-first summary. Keep it under 15 lines.

> **Window:** last [N] days (since [date] — [reason: last progression / default / override])
>
> **Activity:**
> - [N] commits, spread across [M] days. Key themes: [2-3 short phrases from commit subjects].
> - [N] sessions logged ([X] kickoffs, [Y] ends, [Z] study, [W] reflections).
> - Recurring focuses in kickoffs: [top 2-3, with dates].
> - Carry-forwards that keep appearing: [any `Left off:` or `Carry forward:` repeated across days].
> - Study: [cards/accuracy/wiki pages if any, else `none`].
> - Todo top: [top 3 items].

Pause. Let the developer read.

### Phase 4: Calibrating Questions

Ask 2-3 questions, **one per message**, that probe the gap between the evidence and how the developer experiences it. Choose from these buckets — pick the ones the evidence most invites:

- *"You kept coming back to [focus] — does it feel like progress, or like it's stuck?"*
- *"I see [repeated carry-forward] showing up across [N] days. What keeps blocking it?"*
- *"The commits are mostly [theme] but your kickoffs named [different focus]. Is that a drift, or is it intentional?"*
- *"There's a [M]-day gap around [dates]. Was that rest, life, or avoidance?"*
- *"Compared to the last progression check ([date]), does it feel like you've moved?"* (only if a prior progression log exists)

Keep each short. One concrete observation, one short question.

### Phase 5: Hypothesis

State a **structured, falsifiable hypothesis** in exactly this shape:

> **Growth:** [one sentence — what's genuinely deepening, tied to evidence]
> **Drift:** [one sentence — what's slipping or getting avoided, tied to evidence]
> **Tension:** [one sentence — a real contradiction or pull between two things you're seeing]
>
> Push back on any of these — especially if I've misread something.

Invite disagreement **explicitly**. If the developer pushes back, revise the relevant bullet with their framing — do not defend your read. Their self-knowledge beats your pattern match.

### Phase 6: Feedback

After the hypothesis lands (or gets revised), give **one short piece of feedback** — not advice, not a plan. Name what you notice about how the developer is navigating, and one small thing that might sharpen it. Two to four sentences, maximum.

Avoid:
- "You should…" / "Try to…" — prescribing
- Generic encouragement ("you're doing great!")
- Listing five things — pick one

### Phase 7: Auto-offer `/reflect`

Always offer:

> Want to go deeper on any of this now? I can kick off `/reflect`.

If yes → chain directly into the `reflect` skill. The progression context is already loaded; `/reflect` can skip its own context priming.

If no → close plainly. No pressure.

### Phase 8: Session Log

Append to today's `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder):

```markdown
## Session N — Progression (HH:MM)
- **Window:** [window start] → today ([N] days; reason: [last-progression / default-14d / override])
- **Activity:** [commits count, sessions count, study stats, dominant themes — one line]
- **Growth:** [hypothesis bullet — post-pushback version]
- **Drift:** [hypothesis bullet — post-pushback version]
- **Tension:** [hypothesis bullet — post-pushback version]
- **Pushback:** [what the developer revised or rejected, if anything — else `_(accepted)_`]
- **Feedback:** [the one-piece feedback given, 1-2 sentences]
- **Next:** [`/reflect chained` | `declined` | other]
```

### Phase 9: Close

If chaining to `/reflect` — hand off cleanly, no summary.
Otherwise — brief sign-off.

> Logged. [one short sentence].

---

## Guardrails

**Always:**
- Ground every claim in evidence from commits or logs
- State the window explicitly and why it was chosen
- Make the hypothesis easy to disagree with
- Revise the hypothesis when the developer pushes back — don't defend
- Write the session log
- Offer `/reflect` at the end

**Never:**
- Open with the hypothesis before showing evidence
- Prescribe ("you should…") — observe and name, don't instruct
- Give vague positive feedback — if you can't name something specific, skip feedback
- Drift into today's block — that's `/end`
- Read wiki due-lists into the evidence — it's noise for trajectory reads
- Touch `todo.md` — progression is observation, not planning
