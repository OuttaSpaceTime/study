# Scout: Concrete Examples & Flashcard Quality in Study Skills

## Problem

Study skills lack active questioning. Wiki reviews are passive (read → rate). Flashcard quality is never evaluated. Walkthrough/card/flashcard skills have weak "generation effect" prompts.

## Decisions

| Gate | Decision |
|------|----------|
| Wiki review question | Mandatory — one per entry, no skip (Option A) |
| Flashcard quality | Inline flag only, no end-of-session summary (Option A) |
| Example intensity | Every concept: code → coding challenge, theory → understanding question (Option B + A hybrid) |
| Extra flashcard questions | NO — the flashcard IS the question, no layering |

## Scope

### Now
- `study-study`: mandatory concrete question per wiki entry before rating
- `study-study`: inline flashcard quality check (flag genuinely unhelpful cards)
- `study-walkthrough`: strengthen example/challenge per concept
- `study-card`: strengthen example/challenge per concept
- `study-flashcard`: strengthen example/challenge per concept

### Out
- No changes to session logging format
- No changes to rating algorithm
- No new MCP tools
- No extra questions on flashcards during /study

## Files

- `.claude/skills/study-study/SKILL.md` — Phase 2 wiki review + Phase 3 study loop
- `.claude/skills/study-walkthrough/SKILL.md` — Phase 2 walkthrough techniques
- `.claude/skills/study-card/SKILL.md` — Checkpoint 2 unguided mode
- `.claude/skills/study-flashcard/SKILL.md` — Checkpoint 2 per-concept flow
