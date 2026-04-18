# Scout: Unify /kickoff Modes & Flatten Todo List

## Status: COMPLETE — Ready for /plan

## Problem

Redesign `/kickoff` to drop the work/learn mode distinction entirely. Collapse `todo.md` from two sections (`# Work`, `# Learn`) into a single ordered list where top = most important and bubbles up frequently. `/kickoff` should support both quick multi-daily check-ins and single broad-vision runs, helping the developer sort focus, set boundaries, expectations, and time frames. Keep fixed check-in questions, freeform motivational interview, and session logging. Downstream: `/end` currently mirrors work/learn split — must follow.

**Source:** User request, 2026-04-11. Reverses part of scout 003.

## Current State (verified)

- `.claude/skills/kickoff/SKILL.md:25-29` — 3 invocations: `/kickoff`, `/kickoff work`, `/kickoff learn`
- `.claude/skills/kickoff/SKILL.md:35-40` — Phase 1 mode selection
- `.claude/skills/kickoff/SKILL.md:42-64` — Phase 2 reads `todo.md` section by mode
- `.claude/skills/kickoff/SKILL.md:65-85` — Phase 3 fixed questions differ by mode
- `.claude/skills/kickoff/SKILL.md:106-133` — Phase 5 log format differs by mode (`Kickoff/Work` vs `Kickoff/Learn`)
- `.claude/skills/kickoff/SKILL.md:140-147` — Phase 6 handoff differs by mode
- `.claude/skills/end/SKILL.md:25-37` — mode detection from today's kickoff
- `.claude/skills/end/SKILL.md:103-123` — log format differs by mode
- `todo.md:1-5` — `# Work` / `# Learn` sections, Learn has 2 items, Work is empty
- `AGENTS.md:9` — description mentions `(work/learn)`
- `AGENTS.md:22` — documents two-section todo structure
- `.claude/docs/scouts/003-daily-rituals-work-learn-20260410.md` — the scout this partially reverses

## Confirmed Direction (2026-04-11)

- Drop work/learn modes entirely (no invocation args, no mode selection phase, no mode-specific questions, no mode-specific log headers).
- Keep the overall shape: fixed check-in questions → motivational interview → session log.
- Flatten `todo.md` to a single ordered list: top = highest priority, bubbles up each session.
- `/kickoff` is designed to be run multiple times per day (quick refocus) OR once (broad vision).
- `/end` must follow: no mode, unified log format.

## Open Questions

1. **Which fixed questions to keep as the daily trackable set?** (see Checkpoint 1 A/B/C)
2. **Focus-setting mechanics** — how does the flow actually help set boundaries / expectations / time frames?
3. **Todo ordering UX** — does kickoff actively reorder the list, or just ask "is the top still the top?"
4. **Multi-run semantics** — when kickoff runs twice in one day, does session 2 re-ask all fixed questions or a lighter delta?
5. **/end adaptation** — how does /end reflect against a flat todo without a mode lens?

## Decisions

| Gate | Decision |
|------|----------|
| Modes | [DECIDED] Dropped entirely |
| Fixed questions | [DECIDED] Option C: Feeling → Noticing → Focus today → Blockers. Time-framing handled in motivational interview. |
| Todo structure | [DECIDED] Single ordered list, top = highest priority |
| Todo reordering | [DECIDED] Active — after "focus today" answer, Claude proposes reordering ("move X to top?") and applies on confirm |
| Multi-run cadence | [DECIDED] Delta after first run of the day: session 2+ skips Feeling/Noticing, asks only Focus + Blockers |
| Time-framing | [DECIDED] Always prompted as the opener of the motivational interview ("how much time, what's realistic?") — but interview does NOT collapse to just that; full coaching continues after time is set |
| /end adaptation | [DECIDED] Unified log format (no /Work /Learn suffix), reflects against flat ordered todo |
| AGENTS.md | [DECIDED] Update descriptions to remove mode wording, document flat ordered todo |

## Scope

### Now
- **`.claude/skills/kickoff/SKILL.md`** — full rewrite:
  - Remove Phase 1 (mode selection) and `/kickoff work|learn` invocations
  - Phase 2 (todo review): show flat ordered list, light touch
  - Phase 3 (fixed questions): 4 questions — Feeling, Noticing, Focus today, Blockers. Delta-mode for session 2+ of the same day skips Feeling + Noticing
  - Phase 3.5 (new — todo reorder): after "Focus today," propose reorder of `todo.md` based on stated focus, apply on confirm. **Conditional**: only propose if stated focus is not already the top item; otherwise acknowledge and skip
  - Phase 4 (motivational interview): always opens with time-framing ("how much time, what's realistic in that window?"), then continues into full coaching — stuck-points, boundaries, momentum — until developer says stop or natural resolution
  - Phase 5 (session log): unified header `## Session N — Kickoff (HH:MM)`, fields: Feeling, Noticing, Focus, Time, Blockers, Todo updates, Interview notes. Delta sessions log only the fields they asked
  - Phase 6 (handoff): unified. If stated focus maps to wiki pages / flashcards, offer `/study` or `/study-walkthrough`; otherwise plain handoff
- **`.claude/skills/end/SKILL.md`** — mirror changes:
  - Remove Phase 1 mode detection and `/end work|learn` invocations
  - Unified log header `## Session N — End (HH:MM)`
  - Reflection framed against flat ordered list
- **`todo.md`** — collapse to single ordered list (current content: 2 Learn items, Work empty)
- **`AGENTS.md`** — update `/kickoff` + `/end` descriptions; rewrite Todo section to describe flat ordered list
- **`.claude/docs/scouts/003-daily-rituals-work-learn-20260410.md`** — add one-line "Superseded in part by scout 004" note at top

### Later
- Weekly/periodic review skill that scans bottom of `todo.md` for stale items
- Streak/consistency tracking across kickoffs

### Out
- Priority scores, tags, or structured metadata on todo items
- Automated todo pruning
- Migration of historical log entries (old `Kickoff/Work` / `Kickoff/Learn` headers stay)

> If implementation discovers work outside these boundaries, it must STOP and ask — not silently expand scope.

## Risks

1. **Delta detection at date rollover** — accepted, tiny blast radius.
2. **Pushy reordering** — mitigated by conditional proposal (skip if focus = top).
3. **Lost /study chaining cue** — mitigated in unified handoff guidance.
4. **AGENTS.md drift** — prevented by explicit inclusion in file list.
5. **Scout 003 contradiction** — mitigated by superseded note.
