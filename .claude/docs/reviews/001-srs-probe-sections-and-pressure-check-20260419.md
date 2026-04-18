# Review 001 — SRS probe-sections + pressure-check preflight

**Scope:** All staged + unstaged changes on `main` (uncommitted).
**Reviewed:** 2026-04-19
**Change size:** 41 files, ~1671 insertions / 193 deletions.

## Change Intent

Two coupled features:

1. **SRS pressure-check preflight.** New `scripts/srs-pressure` (+ module + tests) that blocks `/study-flashcard` and `/study-walkthrough` (when writing) from piling new material on top of a review backlog. Thresholds: warn at {20 cards / 8 wiki / 5 new-today}, pause at {50 / 20 / 10}. Shared contract document in `.claude/skills/references/srs-pressure-check.md` pulled into both skills as an always-first Preflight.

2. **Per-section SRS probing.** Wiki pages gain `probe_sections` + `last_probed` frontmatter. `/study-study` now probes 1-3 sections per review via a rotating oldest-first queue; `scripts/wiki-reschedule --probed "A,B"` rotates the queue. New lint rules (`probe-section-missing`, `probe-rotation-drift`, `probe-sections-missing`, `probe-index-drift`) enforce consistency. A one-shot `scripts/wiki-backfill-probes` populates existing pages. Orphan check demoted from error to warning (new `allow_orphan` frontmatter override). Wikilink parser now ignores fenced/inline code and image embeds.

Also: `ruff` added to dev deps + `[tool.ruff]` config; frontmatter serialization is now YAML-block across all touched pages.

## Gate Checks

| Check | Result |
|---|---|
| `uv run pytest` | ✅ 123 passed (2.04s) |
| `uv run ruff check scripts/ tests/` | ✅ clean |
| `uv run scripts/lint` | ⚠ 7 orphan warnings, 0 errors |

## Code Areas Inspected

- `scripts/srs_pressure.py` + `scripts/srs-pressure` + `tests/test_srs_pressure.py`
- `scripts/wiki/backfill_probes.py` + `scripts/wiki-backfill-probes` + `tests/test_backfill_probes.py`
- `scripts/wiki/lint.py` (new probe checks, warnings/errors split, wikilink parser rewrite)
- `scripts/wiki/reschedule.py` (new `rotate_last_probed`, `probed` kwarg)
- `scripts/wiki/frontmatter.py` (new `normalize_heading`, probe_sections/last_probed coercion)
- `scripts/wiki/index.py`, `scripts/wiki/write.py`, `scripts/wiki-reschedule`
- `.claude/skills/references/srs-pressure-check.md` (new)
- `.claude/skills/study-flashcard/SKILL.md`, `.claude/skills/study-walkthrough/SKILL.md`, `.claude/skills/study-study/SKILL.md`
- Representative wiki page updates (probe_sections backfill + YAML reformat)

## Findings

| # | Severity | File | Summary | Status |
|---|---|---|---|---|
| 1 | 🛑 blocker | `srs-pressure-check.md` / `study-walkthrough/SKILL.md` | Three-document contradiction on when preflight runs in deepen-focused mode | walked — user confirmed preflight ALWAYS runs first; reference doc + SKILL Phase 4 updated to drop mode-based branching |
| 2 | ⚠️ major | `scripts/wiki/backfill_probes.py` | Backfill writes frontmatter but never updates the index → every backfilled page trips `probe-index-drift` until wiki-write is re-run per page | walked — `backfill_wiki` now calls `update_entry` + `save_index` for every `added` page; new tests `TestBackfillWikiSyncsIndex` lock the contract |
| 3 | ⚠️ major | `scripts/wiki/lint.py:196` | `probe-rotation-drift` is an `error` (exit 1) but is the intended post-deepen state — CI will fail for days until next review | walked — SKILL deepen rule now resets `last_probed` to match updated `probe_sections` instead of letting drift persist; queue invariant holds, no lint error |
| 4 | ℹ️ minor | `scripts/wiki/lint.py:178` | `probe-sections-missing` fires for every page including those not in SRS — intentional per tests, but broad | walked — `AGENTS.md` now documents `probe_sections` / `last_probed` as required fields, matching the lint behavior |
| 5 | ℹ️ minor | `scripts/wiki/backfill_probes.py:93` | Summary doesn't tell the user to re-run `wiki-write` to sync the index (related to #2) | walked — subsumed by #2 (index is now synced in-process; no second step exists) |
| 6 | ⭐ praise | `scripts/srs_pressure.py` | Clean pure-function split (`verdict` / `render_human` / `wiki_due_count` / `main`) with thorough threshold-invariant tests | walked |
| 7 | ⭐ praise | `scripts/wiki/lint.py:24-26` | Wikilink regex now correctly handles `#anchor`, `\|display`, fenced code, inline code, and image embeds | walked |
| 8 | ⭐ praise | `scripts/wiki/reschedule.py:58-65` | `rotate_last_probed` gracefully recovers from drifted state by falling back to `probe_sections` order | walked |

## Post-fix verification

- `uv run pytest` → 125 passed (was 123; +2 new `TestBackfillWikiSyncsIndex` tests)
- `uv run ruff check scripts/ tests/` → clean (also fixed a pre-existing `B905` in `srs_pressure.py:43` — missing `strict=True`)
- `uv run scripts/lint` → 7 orphan warnings, 0 errors (unchanged)

## Open Questions

- **Is the memory authoritative?** `MEMORY.md` records the user feedback "no mode-based branching", which the reference doc contradicts. Need to establish ground truth before resolving finding #1.
- **Is `probe-rotation-drift` meant to fail CI?** The skill says drift is the signal and next review auto-fixes it — but if CI runs `scripts/lint` between deepen and review, it breaks.

## Manual QA Checklist

Cannot execute — this is a skill/CLI repo, no routes. Substitute:

- [ ] Run `scripts/srs-pressure --flashcards-due 25 --human` and confirm `warn` output formats correctly.
- [ ] Run `scripts/srs-pressure --flashcards-due 60 --human` and confirm `pause` output + exit 2.
- [ ] Run `scripts/wiki-backfill-probes --dry-run` against a fresh page without probe_sections and confirm the `would-add` report.
- [ ] Invoke `/study-flashcard` and confirm first assistant message is the preflight verdict (no list_decks / similarity scans before it).
- [ ] Invoke `/study-walkthrough` (no flags) and confirm first message is preflight even in deepen-focused mode.
- [ ] Rate a wiki page via `/study` with `--probed "A,B"` and confirm `last_probed` rotates in both frontmatter AND index.

## Verdict

**Merge-ready.** All findings walked. Blocker resolved via doc alignment, both majors resolved via code + doc fixes (with new test coverage for the index-sync contract). Gates green: 125 tests passing, ruff clean, wiki lint at 7 orphan warnings (unchanged).
