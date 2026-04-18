# Scout: Daily Rituals — /kickoff and /end Commands

> **Partially superseded by [scout 004](004-kickoff-unify-modes-20260411.md) (2026-04-11):** the work/learn mode split and two-section `todo.md` have been dropped. Everything else (shared log file, interview flow, skill boundaries) still stands.

## Status: COMPLETE — Ready for /plan

## Problem

Add two new interactive skills that bookend the workday. `/kickoff` opens with goal-setting, todo review, blockers, and motivational interviewing. `/end` closes with reflection grounded in actual git activity and todo progress. Both serve a personal development cockpit — not project management.

## Decisions

| Gate | Decision |
|------|----------|
| Workspace fit | Belongs here — learning is work, same personal development purpose |
| Skill count | One entry skill (`/kickoff`) with mode selection (work/learn), one closing skill (`/end`) |
| Naming | No prefix for new skills (`kickoff/`, `end/`). Rename existing `study-*` skills later (separate effort) |
| Logs | Same `logs/YYYY-MM-DD.md` file, new section types (Kickoff/Work, Kickoff/Learn, End) |
| Todo file | Single `todo.md` at repo root, `# Work` and `# Learn` sections, checkbox format |
| Fixed questions (both modes) | How are you feeling? / What are you noticing lately? |
| Fixed questions (work) | What do you want to achieve today? / What's blocking you? |
| Fixed questions (learn) | How much time do you have? / What do you want to learn/deepen? / What's blocking you? |
| Freeform interview | Runs until developer says stop OR Claude suggests wrapping up at natural resolution |
| /end behavior | Reads today's logs + todo.md + git log/diff, reflection interview, todo update, closing log |
| CLAUDE.md | Update intro, skills list, document todo.md and ritual flow |

## Scope

### Now
- `.claude/skills/kickoff/SKILL.md` — mode selection, fixed questions, freeform interview, todo read/update, session log
- `.claude/skills/end/SKILL.md` — read today's logs + todo + git activity, reflection interview, todo update, closing log
- `todo.md` at repo root with `# Work` and `# Learn` sections
- CLAUDE.md updates

### Later
- Reflection on past logs (trends, patterns across days)
- Cross-skill integration (kickoff blockers → learn targets → study priorities)
- Rename existing `study-*` skill prefixes

### Out
- No new scripts or tooling
- No changes to existing skills
- No structured mood/energy tracking beyond log text
- No MCP tool dependencies

## Log Format

### Kickoff
```markdown
## Session N — Kickoff/Work (HH:MM)
- **Feeling:** ...
- **Noticing:** ...
- **Goals:** ...
- **Blockers:** ...
- **Todo updates:** ...
- **Interview notes:** [2-3 sentence summary]
```

### End
```markdown
## Session N — End (HH:MM)
- **Achieved:** ...
- **Commits:** ...
- **Carry forward:** ...
- **Reflection:** ...
- **Todo updates:** ...
```

## Files to Create/Modify
- CREATE `.claude/skills/kickoff/SKILL.md`
- CREATE `.claude/skills/end/SKILL.md`
- CREATE `todo.md`
- MODIFY `CLAUDE.md`
