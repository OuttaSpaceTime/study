# SRS Pressure Check

Shared preflight for skills that add new SRS content (`/study-flashcard`, and `/study-walkthrough` when it will write a wiki page). Prevents the developer from piling new material on top of a review backlog.

## Contract (MANDATORY — READ BEFORE ANYTHING ELSE)

This check is a **hard preflight**, not an optional step. It must run **before any other substantive action** in the skill — before listing decks, before reading the wiki index, before drafting anything, before asking the developer what they want to make.

Specifically:

- The **first assistant message** of a skill invocation that will add SRS content must be the pressure-check output. No exceptions.
- No `find_similar_cards`, `list_decks`, `mcp__qmd__query`, or drafting calls may happen before the verdict is produced and (for `warn`/`pause`) surfaced to the developer.
- An assistant message that advances the skill without first surfacing the verdict is a **contract violation** — equivalent to omitting the progress footer.
- "It's just one card" / "the developer already said what they want" / "we ran it earlier in the session" are **not** valid reasons to skip. Run it every invocation.

If you realize mid-flow that the preflight was skipped, stop immediately, run the check, and surface the result before continuing.

## Protocol

1. **Call `mcp__flashcard-mcp__check_pressure` — it is the single source of truth.**

   The tool computes everything server-side from the deck database and returns a structured report. **Do not** call `mcp__flashcard-mcp__get_due_cards` or `mcp__flashcard-mcp__list_decks` for pressure signals — `get_due_cards` caps at 30 and will underreport. The report already includes the per-deck breakdown; reuse that in your status summary instead of a separate `list_decks` call.

   Pressure has **two axes**, both global across all decks:

   | Axis | Field | warn | pause |
   |---|---|---|---|
   | Review backlog | `flashcardsDue` | 20 | 50 |
   | Intake today | `newToday` | 5 | 10 |

   **`flashcardsDue` is the review backlog only — it excludes new cards.** New cards are an optional pool you draw from, not a scheduled backlog, so they never drive review pressure: warning on a pile of fresh material with zero backlog would force `maxNewCards: 0` and you could never start it. Intake is policed by the separate `newToday` axis. The pool is reported on its own as `newAvailable`, for visibility. Consequence: a large pile of *new* cards with no review backlog reads as `ok`, not `warn` — that is correct.

   **Splits of studied cards do not count as intake.** A card created with `inheritFrom` copies its parent's schedule, so it is already-seen material and `newToday` excludes it — splitting a bad card under load is deck maintenance and must never push the verdict up. The one exception is a split off a parent that was never reviewed: it inherits no maturity, so it counts as new material, which is correct.

   **Read the level from the `verdict` field, verbatim** — `ok`, `warn`, or `pause`. Never infer it from prose. When the verdict is `warn` or `pause`, `clearance` gives the exact number of reviews needed to drop the backlog below the warn (and pause) line — `toExitWarn` / `toExitPause`. Carry those numbers through so the developer always knows the count needed to leave the pressure phase. Clearance covers the backlog axis only: no amount of reviewing lowers `newToday`, which resets at the start of the next day.

2. **Surface the result in the first assistant message:**
   - `ok` — one line is sufficient: `SRS pressure: ok — proceeding.` Do not expand. Do not bury it inside a larger message.
   - `warn` — report the counts, the reasons, and the clearance numbers, then ask: "Continue adding new content, or pause and review first?" Wait for an explicit answer before proceeding.
   - `pause` — report the same, then: "I'd recommend pausing here. Want to run `/study` to clear some review load, or continue anyway?" The developer can override with explicit consent ("continue anyway", "I know, keep going") for everything **except** creating new cards — see below.

   **New, unseen cards are hard-blocked at `pause` — not overridable, and not by you.** The flashcard-mcp enforces this itself: `create_card` throws when the verdict is `pause` unless `inheritFrom` is set. The "continue anyway" override never covers a fresh `create_card`, and there is no point attempting one — the server refuses. Still allowed at `pause`, by design: **editing** an existing card (`update_card`) and **splitting** one (`inheritFrom`). Both improve the health of the deck the developer is already carrying, which is exactly what should happen under load. When the verdict is `pause`, redirect to `/study`, an edit, or a split.

3. **Progress footer for the preflight message:** `Preflight — SRS Pressure Check`. (Skills that already have a footer contract follow their own format; this is the footer to emit for this specific step.)

4. **Log it** in the session log if a warning was shown, even if the developer continued. One line: `SRS pressure: <verdict> (<flashcardsDue> due, <newToday> added today) — continued | paused`.

## Where to run it

- `/study-flashcard` — as **Step 1**, before any other tool call. On `ok` the suggestions follow in the same message; on `warn`/`pause` the gate question ends it.
- `/study-walkthrough` — as the **Preflight**, before Phase 1. The first assistant message of the invocation. **Regardless of mode** (write-focused or deepen-focused) and regardless of whether a wiki page will ultimately be written. The developer may opt out of the wiki-write at the end of the session, but the preflight still runs up front.
- `/study` — as the Phase 1 opener. The report is the status summary.

## Do not

- Do not skip the check on the argument that "this is just one card/page". The warning exists because the developer explicitly asked for this guard.
- Do not re-implement the thresholds inline, and do not recompute due counts yourself. Always call `check_pressure`.
- Do not call `mcp__flashcard-mcp__get_due_cards` for the pressure count — it caps at 30.
- Do not query the flashcard SQLite DB directly from a skill. (The wiki-viewer reads it directly to *render* cards; that is a read-only display path, not the pressure path.)
- Do not treat a wiki backlog as pressure. Wiki pages are no longer scheduled — the wiki is for exploration, and only flashcards are studied.
