# SRS Pressure Check

Shared preflight for skills that add new SRS content (`/study-flashcard`, and `/study-walkthrough` when it will write a wiki page). Prevents the developer from piling new material on top of a review backlog.

## Contract (MANDATORY — READ BEFORE ANYTHING ELSE)

This check is a **hard preflight**, not an optional step. It must run **before any other substantive action** in the skill — before listing decks, before reading the wiki index, before drafting anything, before asking the developer what they want to make.

Specifically:

- The **first assistant message** of a skill invocation that will add SRS content must be the pressure-check output. No exceptions.
- No `find_similar_cards`, `list_decks`, `treesearch`, `wiki-search`, or drafting calls may happen before the verdict is produced and (for `warn`/`pause`) surfaced to the developer.
- An assistant message that advances the skill without first surfacing the verdict is a **contract violation** — equivalent to omitting the progress footer.
- "It's just one card" / "the developer already said what they want" / "we ran it earlier in the session" are **not** valid reasons to skip. Run it every invocation.

If you realize mid-flow that the preflight was skipped, stop immediately, run the check, and surface the result before continuing.

## Protocol

1. **Run the pressure script — it is the single source of truth:**

   ```bash
   scripts/srs-pressure --human
   ```

   The script fetches accurate due/new/learning/review counts itself via the flashcard-mcp CLI. **Do not** call `mcp__flashcard-mcp__get_due_cards` or `mcp__flashcard-mcp__list_decks` for pressure signals — `get_due_cards` caps at 30 and will underreport. The script's output already includes a per-deck breakdown; reuse that in your status summary instead of making a separate `list_decks` call.

   Exit codes: `0` ok, `1` warn, `2` pause. Pressure is computed globally across all decks (no category filter).

   **`flashcards due` is the review backlog only — it excludes new cards.** New cards are an optional pool you draw from, not a scheduled backlog, so they never drive review pressure (intake is policed by the separate `cards added today` axis). The script reports the new pool on its own `new available:` line for visibility. Consequence: a large pile of *new* cards with no review backlog reads as `ok`, not `warn` — that is correct; you should learn new cards, not be blocked from starting them.

   **The verdict token is the first line of the output, stated literally:** `SRS pressure: OK` / `SRS pressure: WARN` / `SRS pressure: PAUSE`. Read the level from that token (or from the exit code), **never** from the recommendation prose — the `warn` header reads "we recommend pausing", which is the `warn` level, **not** `pause`. When the verdict is `warn` or `pause`, the output also includes a `To clear pressure:` block giving the exact number of flashcards / wiki pages to review to drop below the warn (and pause) line; carry those numbers through when you surface the result so the developer always knows the count needed to leave the pressure phase.

2. **Surface the result in the first assistant message:**
   - `ok` — one line is sufficient: `SRS pressure: ok — proceeding.` Do not expand. Do not bury it inside a larger message.
   - `warn` — print the **full script output verbatim** (do not summarize or reword — the numbers and reasons are the point), then ask: "Continue adding new content, pause and review first, or **capture this topic excluded from the study loop** (`no-study` — in the wiki, not in review)?" Wait for an explicit answer before proceeding.
   - `pause` — print the full script output verbatim, then: "I'd recommend pausing here. Want to run `/study` to clear some review load, **capture this topic excluded from the study loop** (`no-study` — in the wiki, not in review), or continue anyway?" The developer can override with explicit consent ("continue anyway", "I know, keep going"). Do not proceed with a normal (studied) write without that explicit override — but the `no-study` capture path is always available under pressure, since it adds nothing to the review backlog.

   **Excluded-from-study capture (the `no-study` path).** When the developer chooses this — or says "exclude from study loop" / "don't schedule it" / "just capture it" at any point — write the wiki page normally but add `no-study` to its frontmatter `tags`. `scripts/wiki-write` still fills `next_review`/`review_interval`, but the `no-study` tag keeps the page out of `get_due_entries`, so it never enters review and does not count toward SRS pressure. The page stays a full wiki member otherwise (graph, search, index, links) and renders with a `not in study loop` marker. It rejoins review later via `scripts/wiki-no-study --include`. Because this path adds zero review load, it satisfies the pressure gate on its own — no override needed even at `pause`.

3. **Progress footer for the preflight message:** `Preflight — SRS Pressure Check`. (Skills that already have a footer contract follow their own format; this is the footer to emit for this specific step.)

4. **Log it** in the session log if a warning was shown, even if the developer continued. One line: `SRS pressure: <verdict> (<flashcards_due> cards, <wiki_due> wiki due) — continued | paused`.

## Where to run it

- `/study-flashcard` — as the **Preflight**, before Checkpoint 1. The first assistant message of the invocation.
- `/study-walkthrough` — as the **Preflight**, before Phase 1. The first assistant message of the invocation. **Regardless of mode** (write-focused or deepen-focused) and regardless of whether a wiki page will ultimately be written. The developer may opt out of the wiki-write at the end of the session, but the preflight still runs up front.
- `/study` — as the Phase 1 opener. The script output is the status summary.

## Do not

- Do not skip the check on the argument that "this is just one card/page". The warning exists because the developer explicitly asked for this guard.
- Do not re-implement the thresholds inline. Always call `scripts/srs-pressure`.
- Do not call `mcp__flashcard-mcp__get_due_cards` for the pressure count — it caps at 30. Use the script.
- Do not query the flashcard SQLite DB directly.
- Do not fold the preflight into the first checkpoint — it is a separate, prior step.
