---
name: study
description: "Interactive spaced repetition study session with Claude as evaluator. Reviews due flashcards, rates answers, logs sessions, and supports mid-session actions: discuss, walkthrough, edit, split, delete, reschedule. Trigger keywords: study, review cards, flashcards, spaced repetition."
user_invocable: true
---

# /study — Interactive Spaced Repetition Study Session

## Core Guarantee

The developer leaves each session with reinforced knowledge, accurate card scheduling, and awareness of weak areas. Claude evaluates answers — no self-rating required. The developer can interrupt any card to discuss, edit, split, reschedule, or chain into a walkthrough. The session adapts to the developer, not the other way around.

## Wiki Integration

Flashcards are the only thing studied. The wiki is **not** scheduled and never reviewed on a timer — it is a place to explore after the cards are done. This skill logs session performance to `logs/<MM>/<YYYY-MM-DD>.md`, can trigger wiki writes when gaps are discovered during study, and closes each session by offering pages related to what was actually studied (Phase 4).

**At any point** during the session, the developer can say "show in browser" to open wiki pages related to the current card in the wiki-viewer app. Follow the "Show in browser" flow in `references/wiki-write-protocol.md`.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- ONE card per message, under 150-200 words of prose. Pause for discussion.
- The developer can interrupt at any point — see Mid-Session Actions below.
- Start each card with its position: `Card 3/12 — [Deck Name]`
- After feedback, immediately advance to the next card — do not wait for "next".

## Output Discipline

**Run all lookups silently.** `mcp__flashcard-mcp__check_pressure`, `mcp__flashcard-mcp__check_calibration`, `Read` of wiki pages or the index, `mcp__flashcard-mcp__*` calls — these execute without preamble narration ("Starting Phase 1…", "Let me check…") and without any echoing of their stdout, JSON, or file contents into chat. The chat shows only synthesized output: the pressure verdict line, the question, the rating, the next prompt. If a script exits non-zero or errors, surface a one-line summary, not the stderr blob. This generalizes the existing "read logs, never tail" rule to every tool the skill calls.

## Anti-Overload Principle

- Default to conservative session sizes (5 new + 15 review cards)
- If the developer says "fewer", "less", "short session" — immediately call `adjust_session`
- Never auto-generate cards. Only suggest when a clear gap is observed.
- If the developer has studied today already, acknowledge it
- Show "Session complete" when queue is exhausted — do not pull more cards

## Socratic Never-Reveal on Weak Answers

When the developer's answer is good (would rate Good/Easy), they already produced it — confirm and move on as normal. When the answer is weak (would rate Again/Hard: wrong, blank, or significant gaps), do NOT reveal the card back. Recover via questions instead:

- **Decompose, don't explain.** Ask one smaller guiding question aimed at the missing piece. Point at a concrete value, snippet, error, or the half they did get, and ask what follows. Wait.
- **Never hand over the answer to end the loop.** Keep decomposing into smaller, more concrete questions until the developer produces the missing piece themselves. Hints get more concrete; the final words stay theirs. (Agreed stuck-fallback: decompose, never reveal.)
- **"I don't understand / make it concrete" is NOT a reveal request.** When the developer says the *question* is unclear, asks you to make it concrete, or is confused about what you're asking, make the **next question** smaller and more grounded (a specific value, a one-line snippet, a named scenario) — do **not** answer it for them or work the example to its conclusion. Reformulating the prompt is not the same as supplying the missing piece. This is the most common way revealing sneaks in: a clarification plea gets answered with the full worked solution. Only an *explicit* request for the answer (next bullet) overrides the rule. If you slip and reveal, acknowledge it in one line, rate the section honestly (a revealed section is Again/Hard), and return to decomposition for the remaining sections rather than continuing to explain.
- **Confirming ≠ revealing.** Once they produce it, confirm ("right — that's the piece you were missing"). Do not say it first.
- **Then rate honestly.** Needing scaffolding is the rating signal: a card the developer could only reconstruct under heavy hinting is Again (1) or Hard (2), even though they got there. Submit that rating so the card resurfaces soon.
- **Explicit request override.** If the developer explicitly asks ("just show me the back"), honor it, then re-probe. The rule forbids volunteering the answer, not refusing a direct request.
- **Escape hatch is a walkthrough, not a reveal.** If a card stays stuck after several decomposed hints, rate Again and offer `/study-walkthrough <topic>` rather than dumping the back. Note rating Again re-queues the card for this session (see Intra-day repeats) — after a 3rd failed pass, skip the repeat instead of looping again.

## MCP Server Dependency

This skill requires the `flashcard-mcp` MCP server running from `~/Code/flashcard-mcp`. If tools are not available, tell the user:

> The flashcard-mcp SRS server isn't running. Check `.mcp.json` or run `npm install` in `~/Code/flashcard-mcp`.

## Modes of Invocation

```
/study                    — Start a default study session
/study <deck-name>        — Focus on a specific deck
/study --short            — Short session (5 cards max)
/study add                — Create new flashcards (chain to /study-flashcard)
/study add <deck-name>    — Create flashcards for a specific deck
```

---

## Study Session Flow

### Phase 1: Pressure Check & Status (1 message)

**Three calls, nothing else.** Run `scripts/anki-sync sync` first, then `mcp__flashcard-mcp__check_pressure` and `mcp__flashcard-mcp__check_calibration`. No `get_stats` call, no log reads, no index reads, no extra Bash calls.

`scripts/anki-sync sync` runs **before** the pressure check so reviews done on the phone (via AnkiWeb) land in master.db before due counts are computed. It runs silently; mention it only when it pulled or pushed something (one line, e.g. `Anki sync: pulled 6 phone reviews.`) or when it failed — a failure (offline, not logged in) is a one-line note and the session continues; sync never blocks studying.

`mcp__flashcard-mcp__check_pressure` is the **single source of truth** for due counts and the pressure verdict. Do **not** call `mcp__flashcard-mcp__get_due_cards` for pressure counts — it caps at 30 and underreports. See `references/srs-pressure-check.md` for the full contract.

**Report the `verdict` field verbatim** — `ok`, `warn`, or `pause` — and use exactly that word in your opening line. It is also what sets `maxNewCards` in Phase 2, with no axis-level reinterpretation. Pressure has two axes: `flashcardsDue` (review backlog, excluding the new-card pool) and `newToday` (intake). The pool itself is reported as `newAvailable` and is never pressure.

**Always surface the clearance numbers.** When the verdict is `warn` or `pause`, the `clearance` object states how many reviews drop the backlog below the warn line (`toExitWarn`) and, in `pause`, below the pause line first (`toExitPause`). Carry these into your opening message so the developer always knows the exact count to clear — e.g. "review 12 to exit warn". Clearance is backlog-only: reviewing never lowers `newToday`, which resets at the start of the next day, so say that instead of quoting a number when `newToday` raised the verdict.

**Calibration.** `mcp__flashcard-mcp__check_calibration` reports true retention over the trailing window and a `verdict`: `over-difficult`, `calibrated`, `under-difficult`, or `low-signal`, plus a `marginal` flag. Report the verdict verbatim — never infer it from the retention number, and never recompute retention yourself. It drives the difficulty levers in Phase 2. Surface it as one line in the opening message; if the tool errors, treat the session as `low-signal` (levers stay at their `calibrated` defaults) and note it in one line.

**No leech list is fetched.** Leeches are not surveyed up front any more — the server flags one the moment it serves it and blocks the queue until it is dealt with. See the leech rule in Phase 2.

Emit one opening message with the pressure verdict, the clearance numbers, and the calibration line, then **immediately start Phase 2 (the flashcard loop)** — no confirmation gate, no "ready?".

Example when the verdict is `warn`:

> **Pressure: warn** — 31 flashcards due, 2 added today. `maxNewCards: 0`.
> **To clear:** review 12 to exit warn (31 → 19).
> **Calibration: calibrated** — true retention 87%.
>
> Starting flashcard session.

Example when nothing is due:

> **Pressure:** clear — nothing due today. You're all caught up!
> Want to: add new cards, explore the wiki, or call it a day?

### Phase 2: Flashcard Study Loop (1 card per message)

**`start_session` config — derive `maxNewCards` from the Phase 1 pressure verdict.**

| Pressure verdict | `maxNewCards` | `maxReviewCards` |
|------------------|--------------:|-----------------:|
| `ok` | 5 (default) | 15 (default) |
| `warn` | **0** | 15 |
| `pause` | **0** | 15 |

**The trigger is the overall verdict, whichever axis raised it — never a single axis.** A `warn` raised only by `newToday` still means `maxNewCards: 0`: cards already added today are load the developer has not yet felt, so adding more on top is exactly the move to refuse. Over-adding under load is the recurring failure mode (see `feedback_srs_over_adding`), so do not reason from `flashcardsDue` in isolation to justify pulling new cards. The developer can override explicitly ("include new cards anyway") — pass their requested number and note the override in the session log. At `pause` the server refuses fresh `create_card` calls outright, so an override there can only widen the *study* queue, never create material.

**Surface the cap in the opening line of Phase 2** so the developer never wonders where the new cards went. Example:

> Starting session — 4 due (3 relearning + 1 review), 18 new held back (pressure: warn). `maxNewCards: 0`.

**Difficulty levers — derive from the Phase 1 calibration verdict.** The band percentages below and the 2-point margin restate the constants in flashcard-mcp's `src/core/calibration.ts` — retune them there, then update this table to match.

| Verdict | Staging (`2a`) | Missing-half follow-up | Generation prompt |
|---|---|---|---|
| `over-difficult` (<80%) | on | **off** | off |
| `calibrated` (80-90%) | on | once per card | ~1 in 4 |
| `under-difficult` (>90%) | on, harder framings | up to twice | ~1 in 3, plus "teach it back" |
| `low-signal` | on | once per card | ~1 in 4 |

**`marginal` is a modifier on any of those rows, not a row of its own.** The tool sets it when retention is within 2 points of a band edge; since the bands are hard cutoffs on a noisy estimator, a single review can flip the verdict. When marginal, move **one step back toward the `calibrated` row** rather than applying the verdict's row in full — so a marginal `over-difficult` keeps the follow-up and drops only the generation prompt. `low-signal` is never marginal: that verdict already says retention isn't trustworthy, so distance-to-a-band-edge means nothing there. Never read a marginal verdict as a mandate to strip difficulty.

**The rating rubric is never a lever.** The Again/Hard/Good/Easy definitions in step 4 are fixed and must not shift with the verdict. The loop is self-referential — Claude's own ratings produce the retention number that tunes Claude — so the cheapest way to raise retention would be to grade more leniently. Adjusting *which questions get asked* is in scope; adjusting *what counts as correct* is not, and that boundary is what keeps the metric meaningful.

**State the adjustment when it moves off `calibrated`.** One clause in the Phase 2 opening line, so every automatic softening or sharpening is visible and can be overridden: `Retention 74% (over-difficult) — follow-ups and generation prompts off this session.` The developer can override any lever explicitly ("keep the follow-ups"); honor it and note the override in the session log.

If cards span multiple decks, **interleave** them — don't exhaust one deck before starting the next. Mix topics to strengthen cross-domain connections.

**Intra-day repeats (learning steps).** Any rating that leaves a card in an intra-day learning step re-queues it at the end of the current session — the server appends it with reason `learning_repeat` and `get_next_card` serves it again after the remaining cards. In FSRS terms: Again always repeats; Hard repeats on learning/relearning cards; Good repeats on brand-new cards (10-minute step). A card leaves the session only once its interval is a day or more.

- Mark repeat presentations in the position line: `Card 13/13 — [Deck Name] (repeat)`. The session total grows as repeats are queued — that's expected.
- Evaluate and rate honestly each time. A repeat rated Again comes back again; that's the point.
- On a repeat, **vary the probe** — don't re-ask identically. Ask from a different angle or with a different concrete example so the developer recalls the concept, not your previous phrasing.
- **Stuck-card escape:** if a card fails its 3rd pass in one session, don't keep looping. Rate it honestly, and when it resurfaces, offer `/study-walkthrough <topic>`, call `skip_card`, and move on — it stays due in minutes and returns next session.

**Leech rule (cross-session, distinct from the stuck-card escape above).** The stuck-card escape handles failure *within* one session; this handles a card that keeps failing *across* sessions.

**The server enforces this one — you cannot skip it.** When `get_next_card` serves a card at **5 or more lapses** it stamps the card as a leech and returns `leech: { lapses, mustResolve: true }` alongside it. The *next* `get_next_card` throws until that card is resolved. There is no leech list to consult and no judgement call about whether this one counts: if the payload carries `mustResolve`, the session is blocked until you act.

Review the card normally first — rate it honestly, don't pre-empt the answer. Then, instead of advancing, stop and name it:

> That card is at 7 lapses. Five-plus means the card is fighting you, not the concept — usually the front is too abstract to retrieve against. Rewrite it grounded, split it, or drop it? (Or keep it as-is and I'll stop asking until it fails again.)

The four ways out, and what each does:

| Action | Call | Effect |
|---|---|---|
| **Rewrite** (default) | `update_card` | clears the flag and resets `lapses` to 0 — the failure history belonged to the old wording |
| **Split** | `create_card` with `inheritFrom`, then `delete_card` | new cards keep the schedule but not the flag or the lapse count |
| **Drop** | `delete_card` | card is gone |
| **Keep as-is** | `resolve_leech(cardId, "defer")` | stops blocking until the card lapses *again* |

- **Rewrite is the default fix, not deletion.** Most leeches in this deck are bare definitional fronts (*"What is a parser for a programming language?"*) — the fix is a concrete front per the staging rule in `2a`, baked into the card rather than improvised each session.
- **Do not offer suspend.** It hides the card without fixing it, and a suspended card is never served, so the problem simply stops being visible. Only act on suspend if the developer asks for it by name.
- **Do not propose "defer" first.** It is the escape hatch for a card the developer judges fine as written, not the easy way past the block.
- Since the block is per-card and clears on resolution, a session that hits several leeches will stop several times. That is the intended pressure: it means the deck needs maintenance more than it needs review.
- Record each leech action in the session log (`Leeches:` line).

Then loop:

1. **Call `get_next_card`** — if null, go to Phase 3 (Session Summary)
2. **Present the card front**, followed by a small italic footer listing mid-session actions:
   > *(discuss · edit · split · delete · reschedule · show in browser)*
2a. **Stage the front as a concrete scenario, not a bare prompt.** Default to a fenced snippet, a real header, a JSON payload, or plausible values the developer must reason over, then ask what happens / what breaks / what the output is / what's wrong with a stated claim. Putting a wrong opinion in a colleague's mouth ("A colleague says: …") is a good shape for judgment cards. Example contrast:
   - Weak: *"How do you distinguish a smart from a dumb component?"*
   - Strong: *show two `@Component` classes — one 240 lines taking `@Input()`s, one 12 lines injecting `InvoiceService` — then: "A colleague says the big one is clearly the container. What's wrong with that reasoning, and what's the actual test?"*

   Constraints:
   - **The recall target must not change.** Staging adds surroundings; it never swaps in a different question than the card asks, and never leaks the back into the setup.
   - **Don't stage what's already concrete.** A front that already carries its own snippet or values is presented as written — re-dressing it is ceremony.
   - **Keep the setup short enough to read in one screen.** Elide bodies with `...` / `# 240 lines` rather than inventing filler code.
   - When the question expects a code answer, anchor the expected shape and say a rough outline is fine.
   - **Cloze cards are not staged — they're flagged.** A front containing `{{c1::…}}` is a quality issue (see step 5). Present it as a plain question by reading the deletion as the thing to supply, and raise the rewrite offer after rating. Never author a new cloze.
3. **Wait for the developer's answer**
3a. **Probe option for code-shaped cards.** When the card is code-shaped (git, Python, shell, SQL, HTTP, regex, algorithms) **and** the developer's answer is uncertain, partial, or asserts a specific output, offer one quick probe before evaluating: a `python -c` line, a `git` command, a `curl | jq`, a small unit assertion. The developer runs it and pastes the output. Compare to what they predicted. If prediction and output disagree, name the gap explicitly (`predicted X, got Y`) before rating — that gap is the rating signal, not a side note. Skip the probe entirely for theory-only cards or when the developer's recall was clearly solid — probing in that case is ceremony.
4. **Evaluate the answer** against the card back (and the probe output, when one was run):
   - `Again (1)`: Wrong or fundamentally misses the concept
   - `Hard (2)`: Mostly correct but significant gaps
   - `Good (3)`: Correct answer with reasonable detail
   - `Easy (4)`: Perfect, immediate recall
5. **Feedback** — brief, constructive, and **answer-dependent** (see Socratic Never-Reveal).

   **Precedence on a Good/Easy answer — exactly one of these fires, first match wins.** Several rules below can apply at once; without an order they stack into a three-question interrogation of a card the developer already knew.

   1. **Quality issue** (cloze, too broad, ambiguous, leech) → raise it, stop advancing.
   2. **Missing-half follow-up** → a real second dimension is missing and the verdict allows it.
   3. **Generation prompt** → only if no follow-up fired, at the verdict's rate.
   4. **Nothing** → confirm in one line, rate, advance.

   This also scopes the "advance immediately, don't wait for *next*" rule in Session Rules: it applies to case 4. Cases 1-3 are explicit waits.

   Then, by answer strength:
   - **Good/Easy answer:** keep it tight — **2-3 sentences, hard cap.** The developer already produced the answer, so don't re-explain it back to them. Spend the sentences only on filling a genuine gap or drawing one interesting/non-obvious connection, and only when there is one — a clean answer can just get a one-line confirm + rating. Do not volunteer a deeper expansion; the developer will ask ("discuss", "tell me more") if a card is worth dwelling on. The goal on good answers is to keep moving; Socratic depth is for the cards that need it (weak answers), not for cards already known.
   - **Missing-half follow-up — ask for the gap, don't fill it.** When the answer is *correct* but covers only one of two things the back requires (one of a pair, one of two conditions, one side of a contrast), do not supply the other half as feedback. Confirm the half they got in one clause, then ask for the missing one as a fresh question — best done by moving the goalposts to a case that isolates it. Example: the card asks why a copied CSP nonce fails; the developer says *"the nonce is unique per request"* (freshness, but not unpredictability) →
     > Right that it's fresh per response — so the attacker's copied value is already stale. One more: suppose the server regenerated it per request but used `nonce-` plus a 3-digit counter (001, 002, …). Per-request unique, still. Is that safe?

     This does not violate the 2-3 sentence cap above — the cap governs *explaining*, and this is asking. Rate once, after the follow-up, on the whole exchange: producing the missing half unaided is still Good; needing it decomposed further is Hard. Fire it at the rate the calibration verdict sets (**at most once per card** on `calibrated`, off on `over-difficult`), and only when the gap is a real second dimension — not to extract a synonym or a detail the back doesn't ask for. A second miss goes to Socratic recovery below.
   - **Again/Hard answer:** do NOT reveal the back. Enter Socratic recovery — decompose into smaller guiding questions until the developer produces the missing piece themselves, then confirm. Never volunteer the answer to close the loop.
   - State what was correct and what was missing (1-2 sentences)
   - **Do not state the rating yet.** The rating line is emitted *once*, after `submit_review` returns (step 6), so it can carry the next interval. Decide the rating here (needing recovery hints means Again/Hard) but do not print a bare "Rated: …" line in this step — printing it here and again in step 6 double-states it.
   - **Flashcard quality check:** Evaluate the card itself — not just the answer. Flag genuinely weak cards:
     - **Too vague:** back doesn't give enough concrete detail to learn from (not just short — a precise one-liner is fine)
     - **Too broad:** front covers multiple distinct concepts that should be separate cards
     - **Outdated:** code examples reference deprecated APIs or patterns no longer in use
     - **Ambiguous front:** question is unclear without seeing the back
     - **Non-atomic / opinion-bait front:** front asks for a superlative or judgment ("the single most effective", "the best way", "the right approach") or otherwise admits several defensible answers, so there is no single recall target. The fix is to name the specific scenario or principle being tested — e.g. rewrite "What's the single most effective technique for loose coupling?" to "Which design principle reduces coupling by depending on an abstraction instead of a concrete collaborator?". Distinct from *Too broad* (many concepts) and *Ambiguous front* (unclear meaning): here the meaning is clear but the answer space is open.
     - **Mismatched Q/A:** front asks "what" but back explains "why", or vice versa
     - **Cloze format:** front contains `{{c1::…}}`. Cards must be question/answer style — a cloze hands over the sentence frame, so it tests recognition of a missing word rather than a full retrieval attempt. Offer to rewrite it as one or more Q/A cards with `inheritFrom`. A cloze carrying **two facts in one deletion** (e.g. `{{c1::all requests}}` … `{{c1::the Secure attribute}}`) is also a one-fact-per-card violation and splits into separate cards.
     - **Verbose answer:** the back pads the answer with a restated question, a trailing summary clause, or a second idea the front never asked for. Answers are capped at **200 visible characters and 4 sentences** (enforced by `update_card`), and the fix is almost always to cut filler rather than to split. Offer the tightened wording directly instead of asking the developer to draft it.
     - **Two questions on the front:** the front asks two things ("what does X do <b>and</b> what is its default?"). Keep the one the card is really about; split only if the dropped idea has no other card (check with `search_cards`).
     - Do NOT flag cards that are intentionally minimal — simple recall cards with precise, correct backs are fine.
     - **When a quality issue is detected: stop advancing.** Explicitly describe the problem and ask the developer to fix it before continuing. Example: "This card's front is ambiguous — it could mean X or Y. Want to edit it to be more specific, or split it?" Wait for the developer to edit, split, or explicitly say "skip" before moving on.
   - **Generation prompt** (on Good/Easy cards, at the rate the calibration verdict sets — see the difficulty-lever table; off entirely on `over-difficult`): Ask the developer to generate their own example or analogy: "Can you give me a real-world scenario where this applies?" This strengthens encoding. Keep it brief — one sentence is enough.
   - One-liner reminder: *(harder/easier · discuss · edit · split · delete · show in browser)*
6. **Call `submit_review`** with the rating, then state the rating line **once** — complete with the next interval from the returned schedule (`due`, `interval`, `state`, `intraDay`). This is the only place the rating is printed. Read the schedule silently; show only the formatted phrase, never the raw JSON. Format:
   - `intraDay: true` (interval `0`) → "Rated: **Again (1)** — repeats this session". Don't invent a minute count.
   - `interval >= 1` → "Rated: **Good (3)** — next review in **N days** (YYYY-MM-DD)" using `interval` and the date portion of `due`. Use "1 day" (singular) when `interval` is 1.
7. **Advance** — call `get_next_card` and present the next card in the same message. Only advance if no quality issue was flagged (or developer resolved/skipped it).

**Track session data** internally for the log:
- Cards reviewed (unique cards), repeats served, ratings given, lapses (Again ratings), start time

### Phase 3: Session Summary (1 message)

> **Session complete** — 12 cards in 11 minutes
> Accuracy: 83% | Streak: 5 days
>
> Weak areas: Deck B (2 lapses), Deck C (1 lapse)
> Leech: "What is a parser…" (7 lapses) — rewritten grounded, schedule inherited

**Duration must be honest — measure the exchange, not the session row.** `start_session`'s `startTime` is when the session was *opened*, which historically has spanned hours of idle terminal (17 cards over 5h56m on 2026-07-22). Time the interval from the **first card presented to the last review submitted**, and:

- Under 2 hours → report it plainly: `12 cards in 11 minutes`.
- Over 2 hours, or interrupted by a long gap → report cards and accuracy, and mark the span as inclusive of breaks: `17 cards over 5h56m (with breaks)`. Never present an idle-inflated span as study time.
- Never invent a duration you didn't observe. If the session's start is unknown (resumed context, unclear first card), omit the duration line rather than estimating.

**Close the session with `end_session`.** After the summary, call `end_session` with the session id. Reviews do not close a session — `submit_review` no longer stamps `endTime`, so `endTime` now means "this session was ended" and nothing else. Call it here and on every exit path: "done" / "stop" / "end", and when a session is abandoned mid-way. The call is idempotent, so calling it twice is harmless. Also don't call `start_session` until Phase 2 actually begins — never speculatively in Phase 1.

A session that reviewed nothing is discarded automatically the next time `start_session` runs, so abandoned empty rows no longer pile up. A session that *did* review cards and was never closed keeps `endTime: null` on purpose — we don't know when it ended, and stamping it later would invent a duration.

### Phase 4: Session Log & Wiki Exploration

**Write session log** — append to `logs/<MM>/<YYYY-MM-DD>.md` (create if doesn't exist):

```markdown
## Session N — Study (HH:MM)
- **Cards reviewed:** 12 (+3 intra-day repeats)
- **Accuracy:** 83%
- **Calibration:** calibrated (true retention 87%) — levers at default
- **Lapses:** event sourcing (Again), CQRS (Hard)
- **Leeches:** "What is a parser…" (7 lapses) → rewritten grounded, schedule inherited
- **Duration:** 11 min
- **Wiki explored:** [[rails/database-transactions]], [[rails/row-locking-and-concurrency]]
- **Surprising:** <one card/concept the developer thought they knew but lapsed on, or vice versa — skip if nothing stood out>
- **Heuristic:** <one sentence a future study session in this area should read first — skip if none surfaced>
```

The `Surprising` and `Heuristic` fields are optional on `/study` (unlike `/study-walkthrough` where they're mandatory in Learning cadence). Write them only when the session actually produced a surprise or a generalizable rule — a routine clean-accuracy session doesn't need them. When present, they compound across sessions and feed `/progress` and `/reflect`.

Omit the **Wiki explored** line if the developer opened nothing.

**Lapse names are plain text, never wikilinks.** Write the card's topic name directly (e.g., "event sourcing"), not `[[architecture/event-sourcing]]`. Lapses refer to flashcard topics, which may not have wiki pages — linking them creates broken wikilinks.

**Push reviews to AnkiWeb.** After the session log, run `scripts/anki-sync sync` silently to push this session's reviews and any card changes. One-line confirm only if it moved something (e.g. `Anki sync: pushed 12 reviews.`); on failure, a one-line note — never re-run automatically or block the wrap-up.

**Wiki explored entries use bare wikilinks, never backticked.** Write `[[architecture/event-sourcing]]` not `` `[[architecture/event-sourcing]]` ``. Backticks prevent Obsidian from rendering clickable links.

**Repeated lapse detection:** Read recent session logs to detect cross-session repeat lapses. If a topic has lapsed 3+ times across the past 7 days and has no wiki page, recommend `/study-walkthrough <topic>` — but keep the recommendation to a single sentence. Do not print the supporting log excerpts or per-session breakdowns.

#### Wiki exploration offer (after the log, before the closing offers)

The wiki is no longer scheduled, so nothing is ever "due" — instead, close the session by pointing at pages connected to what was **actually studied**. This is an invitation, not a queue: the developer opens what interests them, reads at their own pace, and nothing is rated or rescheduled.

**Find the pages** by matching this session's card ids against the index, silently:

1. Read `wiki/.wiki-index.json` and collect entries whose `flashcard_ids` contain any card served this session.
2. If that yields nothing, fall back to tag overlap between the studied cards and page `tags`.
3. Rank by how many of the session's cards a page covers, and prefer pages tied to cards that lapsed — a page attached to a miss is worth more than one attached to an easy hit.

The viewer's dashboard ranks the same kind of list by recency first (`wiki-viewer/app/lib.ts`). That is deliberately a different order, not a bug to reconcile: the dashboard spans weeks, where "when did I last touch this" is the useful sort, while here every card came from the session that just ended, so recency is uniform and coverage is the only signal left.

**Offer at most 3**, as one short message with a one-clause reason each:

> Studied 12 cards. Related pages: [[rails/database-transactions]] (4 of today's cards), [[rails/row-locking-and-concurrency]] (2, including the one you lapsed on). Want either open, or shall I open the wiki index to browse?

- On a "yes"/page name, open it with the "Show in browser" flow from `references/wiki-write-protocol.md`, then stay available for questions or refinements. Do **not** re-open it as a review loop, do not ask section questions, do not rate it.
- **If no page matches at all** — the common case for a deck topic with no wiki coverage yet — do not force a suggestion. Open the index view for free exploration instead: `xdg-open "http://localhost:4777/"`. Mention it in one line: "Nothing in the wiki maps to today's cards — opening the index if you want to browse."
- If a topic lapsed repeatedly and has no page, that is the moment to offer `/study-walkthrough --write <topic>` rather than a page to read.
- Record whatever the developer actually opened in the **Wiki explored** log line.

**Post-session offers:**
- `/study-walkthrough <topic>` for struggling areas — "You had 2 lapses on event sourcing. Want to deepen that with /study-walkthrough?"
- `/study-flashcard` to create cards for gaps discovered during session
- `/study-walkthrough --write <topic>` to create a reference page for a topic you struggled with

---

## Mid-Session Actions

The developer can say any of these at any point during the study loop.

### "discuss" / "tell me more" / "why?" / "I don't understand"

Pause the session. Explain the concept in more depth, using concrete code when possible. Keep discussion to 2-4 exchanges. When the developer demonstrates understanding, resume the study loop.

### "walkthrough" / "let's go deeper"

Pause the session. Note: "Pausing study session — we'll pick up where we left off."
Chain into `/study-walkthrough` on the current card's topic. When complete, ask: "Ready to continue studying? You have N cards left."

### "edit" / "this card is wrong" / "fix this card"

Show current front and back. Developer provides corrections. Call `update_card`. Resume.

**Card content format (edit & split):** any front/back written via `update_card`/`create_card` must use the simple-HTML format from `/study-flashcard`'s "Card Content Format" section (`<br>`, `<code>`, `<b>`, `<ul>`, entities for literal `<`/`>`) — never markdown or bare newlines. Cards sync to Anki, which renders fields as HTML. Present drafts in chat rendered, not as raw HTML.

**Card size limits (edit & split):** the back must be at most **200 visible characters** and **4 sentences**, and the front must ask **one question**. Both are enforced by `update_card`, which rejects a violating edit with a per-field error naming the remedy. Markup does not count toward the limit, and fronts have no length cap. See "Card Size & Scope" in `/study-flashcard`. When an edit is rejected, reduce the text first — splitting adds review load and is the last resort.

### "actually, your last explanation was wrong" / correction mid-feedback

**Correction Primitive.** If the developer corrects an explanation you gave in the feedback for a previous card (not the card itself), do not argue or layer a second explanation on top. Acknowledge in one line ("Got it — the correct answer is X"), re-state the correction cleanly, and carry the corrected version forward for any later card on the same topic. If a card whose feedback was wrong has already been rated, do not silently re-rate it — offer: "I gave you bad feedback on card N. Want me to reschedule it as Again/Hard so you see it again soon?" Let the developer decide.

### "split" / "this card is too big"

Show current card. Developer identifies distinct concepts. Draft focused cards for each. Create new cards, delete original (or ask if the original is worth keeping in a narrower form). Resume.

**Prefer reducing over splitting.** The developer's standing preference: when a card is merely wordy, or its extra concept is already covered by another card, tighten the answer in place with `update_card` rather than splitting. Splitting is right when the card genuinely carries two ideas that both need their own retrieval. Say which one you are doing and why before you do it.

**Inherit the original's schedule — never reset split cards to fresh.** When the original card already had review history (state `review`/`relearning`, a non-zero interval), the new cards must keep that maturity. Pass `inheritFrom: <original card id>` to **every** `create_card` call in the split so each new card copies the original's FSRS block (due, stability, difficulty, reps, lapses, state, lastReview, interval — maturity is derived from state and interval, so it follows automatically). Splitting is a re-phrasing of material the developer already knows at that interval — fresh cards would wrongly resurface it immediately. Do this **before** deleting the original (you need its id, and the inheritance reads the live row). After creating, state the inherited interval from each card's returned `interval`/`due` (e.g. "4 cards created, each inheriting the original's schedule — next due 2026-09-11"). The same rule applies whenever a new card is derived from an existing one, not only on explicit "split". Do not offer to fake a review or seed an arbitrary interval — `inheritFrom` is the supported, exact mechanism.

### "delete" / "drop this card" / "this card is useless"

Delete the card via `delete_card`. Do not counter-offer suspend — adding new cards is cheap; preserving review history on a bad card is not valuable. One-line confirm is fine for borderline cases ("delete permanently — sure?"), but on an unambiguous instruction just act. Resume.

### "reschedule" / "show this later" / "not now"

Ask when to resurface. Rate accordingly to push FSRS scheduling out. Resume.

### "skip"

Call `skip_card`, advance to next.

### "done" / "stop" / "end"

Go to Phase 3 (Session Summary) with whatever was reviewed, then Phase 4 — which includes calling `end_session`. Stopping early still closes the session.

### "fewer" / "less" / "shorten"

Call `adjust_session`. Confirm reduction. Continue.

### "add" / "new card"

Chain to `/study-flashcard` with current deck. After creation, resume.

### "show in browser" / "open in browser"

Follow the "Show in browser" flow from `references/wiki-write-protocol.md`. If a wiki page exists for the current card's topic, open it. If not, offer to create one. Resume session after.

---

## Rating Override

If developer says "actually harder" or "actually easier" after feedback, acknowledge and adjust. The already-submitted rating is persisted; factor self-assessment into future evaluations of this card.

## Guardrails

**Always:**
- Reference actual codebase code when discussing card concepts
- On a weak (Again/Hard) answer, recover via smaller questions — never volunteer the back (Socratic Never-Reveal)
- Respect every mid-session action immediately
- Write session log at the end of every session
- Call `end_session` on every exit path — normal wrap-up, "done"/"stop", or abandoning mid-way
- Link lapses to wiki pages when they exist

**Never:**
- Author a cloze-deletion card (`{{c1::…}}`) — cards are question/answer style, and existing clozes get offered a Q/A rewrite
- Let the calibration verdict touch the rating rubric — see "The rating rubric is never a lever" in Phase 2
- Stack more than one follow-up onto a Good answer — see the precedence list in step 5
- Report a duration you didn't measure — see the duration rule in Phase 3
- Show the answer before the developer attempts a response
- Reveal the back to fill a gap on a weak answer — decompose into a smaller question instead (explicit developer request excepted)
- Create cards automatically
- Batch multiple cards in one message
- Schedule, reschedule, or rate a wiki page — pages carry no review state; the wiki is explored, not studied
- Probe a wiki page with questions, or turn the Phase 4 exploration offer into a review queue
- Ignore mid-session requests
- Skip the session log
