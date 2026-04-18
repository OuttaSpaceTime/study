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

1. **Query the MCP** (always — never read the flashcard DB directly):
   - Call `mcp__flashcard-mcp__get_due_cards` — use `.count` from the response.
   - Call `mcp__flashcard-mcp__list_decks` — sum `stats.newToday` (or equivalent) across decks for the "added today" signal. If unavailable, pass `0`.

2. **Run the pressure script** (it reads wiki due from the index):

   ```bash
   scripts/srs-pressure --flashcards-due <N> --new-today <M> --human
   ```

   Exit codes: `0` ok, `1` warn, `2` pause.

3. **Surface the result in the first assistant message:**
   - `ok` — one line is sufficient: `SRS pressure: ok — proceeding.` Do not expand. Do not bury it inside a larger message.
   - `warn` — print the **full script output verbatim** (do not summarize or reword — the numbers and reasons are the point), then ask: "Continue adding new content, or pause and review first?" Wait for an explicit answer before proceeding.
   - `pause` — print the full script output verbatim, then: "I'd recommend pausing here. Want to run `/study` to clear some review load, or continue anyway?" The developer can override with explicit consent ("continue anyway", "I know, keep going"). Do not proceed without that explicit override.

4. **Progress footer for the preflight message:** `Preflight — SRS Pressure Check`. (Skills that already have a footer contract follow their own format; this is the footer to emit for this specific step.)

5. **Log it** in the session log if a warning was shown, even if the developer continued. One line: `SRS pressure: <verdict> (<flashcards_due> cards, <wiki_due> wiki due) — continued | paused`.

## Where to run it

- `/study-flashcard` — as the **Preflight**, before Checkpoint 1. The first assistant message of the invocation.
- `/study-walkthrough` — as the **Preflight**, before Phase 1. The first assistant message of the invocation. **Regardless of mode** (write-focused or deepen-focused) and regardless of whether a wiki page will ultimately be written. The developer may opt out of the wiki-write at the end of the session, but the preflight still runs up front.

## Do not

- Do not skip the check on the argument that "this is just one card/page". The warning exists because the developer explicitly asked for this guard.
- Do not re-implement the thresholds inline. Always call `scripts/srs-pressure` so the logic stays in one place.
- Do not query the flashcard SQLite DB directly. Always go through the MCP.
- Do not fold the preflight into the first checkpoint — it is a separate, prior step.
- Do not run other skill tool calls (deck listing, wiki index reads, similarity scans) before the verdict is surfaced.
