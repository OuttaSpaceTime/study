---
name: study
description: "Interactive spaced repetition study session with Claude as evaluator. Reviews due flashcards, rates answers, logs sessions, and supports mid-session actions: discuss, walkthrough, edit, split, delete, reschedule. Trigger keywords: study, review cards, flashcards, spaced repetition."
user_invocable: true
---

# /study — Interactive Spaced Repetition Study Session

## Core Guarantee

The developer leaves each session with reinforced knowledge, accurate scheduling, and awareness of weak areas. Claude evaluates answers — no self-rating required. The developer can interrupt any card to discuss, edit, split, reschedule, or chain into a walkthrough. The session adapts to the developer, not the other way around.

## Wiki Integration

This skill logs session performance to `logs/<MM>/<YYYY-MM-DD>.md`. It can also trigger wiki writes when gaps are discovered during study.

**At any point** during the session, the developer can say "show in browser" to open wiki pages related to the current card in the wiki-viewer app. Follow the "Show in browser" flow in `references/wiki-write-protocol.md`.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- ONE card per message, under 150-200 words of prose. Pause for discussion.
- The developer can interrupt at any point — see Mid-Session Actions below.
- Start each card with its position: `Card 3/12 — [Deck Name]`
- After feedback, immediately advance to the next card — do not wait for "next".

## Output Discipline

**Run all lookups silently.** `scripts/srs-pressure`, `scripts/wiki-due`, `Read` of wiki pages or the index, `mcp__flashcard-mcp__*` calls — these execute without preamble narration ("Starting Phase 1…", "Let me check…") and without any echoing of their stdout, JSON, or file contents into chat. The chat shows only synthesized output: the pressure verdict line, the wiki-due numbered list, the question, the rating, the next prompt. If a script exits non-zero or errors, surface a one-line summary, not the stderr blob. This generalizes the existing "read logs, never tail" rule to every tool the skill calls.

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

This skill requires the `flashcard-mcp` MCP server running from `~/Code/Misc/flashcard-mcp`. If tools are not available, tell the user:

> The flashcard-mcp SRS server isn't running. Check `.mcp.json` or run `npm install` in `~/Code/Misc/flashcard-mcp`.

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

**Three script calls, nothing else.** Run `scripts/anki-sync sync` first, then `scripts/srs-pressure --human` and `scripts/wiki-due` — these are the only lookups in Phase 1. No log reads, no index reads, no extra Bash calls.

`scripts/anki-sync sync` runs **before** the pressure check so reviews done on the phone (via AnkiWeb) land in master.db before due counts are computed. It runs silently; mention it only when it pulled or pushed something (one line, e.g. `Anki sync: pulled 6 phone reviews.`) or when it failed — a failure (offline, not logged in) is a one-line note and the session continues; sync never blocks studying.

`scripts/srs-pressure --human` is the **single source of truth** for flashcard due counts and the pressure verdict. Do **not** call `mcp__flashcard-mcp__get_due_cards` for pressure counts — it caps at 30 and underreports.

**Report the verdict token verbatim — never infer it from the prose.** The first line of `scripts/srs-pressure --human` is the canonical verdict: `SRS pressure: OK`, `SRS pressure: WARN`, or `SRS pressure: PAUSE`. Use exactly that word (`ok` / `warn` / `pause`) in your opening line. Do **not** read the level off the recommendation prose — the `warn` header contains the phrase "we recommend pausing", which is *not* the `pause` verdict. (`warn` = "we recommend pausing"; `pause` = "Danger! …well past the recommended pause point".) When the level matters for `maxNewCards`, it is driven by the `flashcards due` axis per the Phase 2 table, independent of which axis triggered the overall verdict.

**Always surface the clearance numbers.** When the verdict is `warn` or `pause`, the script prints a `To clear pressure:` block stating, per axis, how many flashcards / wiki pages must be reviewed to drop below the warn line (and, in `pause`, below the pause line first). Carry these numbers into your opening message verbatim so the developer always knows the exact count to clear to leave the pressure phase — e.g. "clear 12 wiki pages to exit warn". The same numbers are in the `clearance` object of `--json` if you need them programmatically.

`scripts/wiki-due --human` returns the full formatted list of due wiki entries. Print it directly in the opening message — this is informational only, wiki review happens after flashcards (Phase 3).

Emit one opening message with the pressure verdict, the clearance numbers, the wiki due list, then **immediately start Phase 2 (flashcard loop)** — no confirmation gate, no "ready?", no "say open N".

Example when the verdict is `warn` (driven by the wiki axis):

> **Pressure: warn** — 19 flashcards due (below the 20 warn line), 19 wiki pages due. `maxNewCards: 0`.
> **To clear:** review 12 wiki pages to exit warn (19 → 7). Flashcards are already below their warn line.
>
> **Wiki due (19):**
> 1. [[reactive/observables]] — due 2026-05-20 (interval: 8d)
> 2. [[reactive/reactive-programming]] — due 2026-05-20 (interval: 8d)
> …
>
> Starting flashcard session.

Example when nothing is due:

> **Pressure:** clear — nothing due today. You're all caught up!
> Want to: add new cards, revisit a wiki page with /study-walkthrough, or call it a day?

### Phase 2: Flashcard Study Loop (1 card per message)

**`start_session` config — derive `maxNewCards` from the Phase 1 pressure verdict.**

| Pressure verdict | `maxNewCards` | `maxReviewCards` |
|------------------|--------------:|-----------------:|
| `ok` (< 20 due) | 5 (default) | 15 (default) |
| `warn` (≥ 20 due) | **0** | 15 |
| `pause` (≥ 50 due) | **0** | 15 |

The warn-threshold cap exists because over-adding under load is the recurring failure mode (see `feedback_srs_over_adding`). The pressure script's `flashcards due` count is the trigger — not the wiki/new-today axes. Note `flashcards due` is the **review backlog only** (learning + review + relearning); it excludes the new-card pool, which the script reports separately as `new available`. So a deck with many new cards and no backlog reads `ok` and pulls the default 5 new — new material is meant to be learned, not held back. The developer can override explicitly ("include new cards anyway") — pass their requested number and note the override in the session log.

**Surface the cap in the opening line of Phase 2** so the developer never wonders where the new cards went. Example:

> Starting session — 4 due (3 relearning + 1 review), 18 new held back (pressure: warn). `maxNewCards: 0`.

If cards span multiple decks, **interleave** them — don't exhaust one deck before starting the next. Mix topics to strengthen cross-domain connections.

**Intra-day repeats (learning steps).** Any rating that leaves a card in an intra-day learning step re-queues it at the end of the current session — the server appends it with reason `learning_repeat` and `get_next_card` serves it again after the remaining cards. In FSRS terms: Again always repeats; Hard repeats on learning/relearning cards; Good repeats on brand-new cards (10-minute step). A card leaves the session only once its interval is a day or more.

- Mark repeat presentations in the position line: `Card 13/13 — [Deck Name] (repeat)`. The session total grows as repeats are queued — that's expected.
- Evaluate and rate honestly each time. A repeat rated Again comes back again; that's the point.
- On a repeat, **vary the probe** — don't re-ask identically. Ask from a different angle or with a different concrete example so the developer recalls the concept, not your previous phrasing.
- **Stuck-card escape:** if a card fails its 3rd pass in one session, don't keep looping. Rate it honestly, and when it resurfaces, offer `/study-walkthrough <topic>`, call `skip_card`, and move on — it stays due in minutes and returns next session.

Then loop:

1. **Call `get_next_card`** — if null, go to Phase 3 (Wiki Review)
2. **Present the card front**, followed by a small italic footer listing mid-session actions:
   > *(discuss · edit · split · delete · reschedule · show in browser)*
3. **Wait for the developer's answer**
3a. **Probe option for code-shaped cards.** When the card is code-shaped (git, Python, shell, SQL, HTTP, regex, algorithms) **and** the developer's answer is uncertain, partial, or asserts a specific output, offer one quick probe before evaluating: a `python -c` line, a `git` command, a `curl | jq`, a small unit assertion. The developer runs it and pastes the output. Compare to what they predicted. If prediction and output disagree, name the gap explicitly (`predicted X, got Y`) before rating — that gap is the rating signal, not a side note. Skip the probe entirely for theory-only cards or when the developer's recall was clearly solid — probing in that case is ceremony.
4. **Evaluate the answer** against the card back (and the probe output, when one was run):
   - `Again (1)`: Wrong or fundamentally misses the concept
   - `Hard (2)`: Mostly correct but significant gaps
   - `Good (3)`: Correct answer with reasonable detail
   - `Easy (4)`: Perfect, immediate recall
5. **Feedback** — brief, constructive, and **answer-dependent** (see Socratic Never-Reveal):
   - **Good/Easy answer:** keep it tight — **2-3 sentences, hard cap.** The developer already produced the answer, so don't re-explain it back to them. Spend the sentences only on filling a genuine gap or drawing one interesting/non-obvious connection, and only when there is one — a clean answer can just get a one-line confirm + rating. Do not volunteer a deeper expansion; the developer will ask ("discuss", "tell me more") if a card is worth dwelling on. The goal on good answers is to keep moving; Socratic depth is for the cards that need it (weak answers), not for cards already known.
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
     - Do NOT flag cards that are intentionally minimal — simple recall cards with precise, correct backs are fine.
     - **When a quality issue is detected: stop advancing.** Explicitly describe the problem and ask the developer to fix it before continuing. Example: "This card's front is ambiguous — it could mean X or Y. Want to edit it to be more specific, or split it?" Wait for the developer to edit, split, or explicitly say "skip" before moving on.
   - **Generation prompt** (on Good/Easy cards, ~1 in 4 cards): Ask the developer to generate their own example or analogy: "Can you give me a real-world scenario where this applies?" This strengthens encoding. Keep it brief — one sentence is enough.
   - One-liner reminder: *(harder/easier · discuss · edit · split · delete · show in browser)*
6. **Call `submit_review`** with the rating, then state the rating line **once** — complete with the next interval from the returned schedule (`due`, `interval`, `state`, `intraDay`). This is the only place the rating is printed. Read the schedule silently; show only the formatted phrase, never the raw JSON. Format:
   - `intraDay: true` (interval `0`) → "Rated: **Again (1)** — repeats this session". Don't invent a minute count.
   - `interval >= 1` → "Rated: **Good (3)** — next review in **N days** (YYYY-MM-DD)" using `interval` and the date portion of `due`. Use "1 day" (singular) when `interval` is 1.
7. **Advance** — call `get_next_card` and present the next card in the same message. Only advance if no quality issue was flagged (or developer resolved/skipped it).

**Track session data** internally for the log:
- Cards reviewed (unique cards), repeats served, ratings given, lapses (Again ratings), start time

### Phase 3: Wiki Review (after flashcards)

When the flashcard queue is exhausted, review the due wiki pages **in the order `scripts/wiki-due` returned them — most due first, least due last.** Do not ask the developer which page to open; do not present the list again as a menu. Start immediately with the most-due page and walk down the list one page at a time. The only choices the developer makes are per-page actions (next / discuss / walkthrough / skip) and the global escape ("skip wiki" / "done with wiki" → Phase 4).

> **Flashcards done.** 11 wiki pages are due. Going through them most-due first — say "skip wiki" any time to jump to the summary.
>
> First up: [[llm/embeddings-vs-embedding-layer]].

If there were no due wiki entries, go straight to Phase 4.

**Review loop for each entry** (start at the top of the due list, advance down it):

1. Take the next page in due order automatically — no "which one?" prompt.
2. Read the wiki page. Present a brief summary: title, sections, current interval — but do NOT open the browser page yet.
3. **Pick sections to probe — rotation via `last_probed`:**

   Read `probe_sections` and `last_probed` from the page's YAML frontmatter. `last_probed` is an ordered queue (oldest first); treat as `probe_sections` order if empty.

   Choose `n = min(len(probe_sections), 3)` sections — the first `n` from the queue. You will ask **one focused question per section, cap 3 total — but strictly one question per message.** Never list two or three questions together or say "take them in order." Ask the first section's question, wait for the answer, evaluate it, then ask the next section's question in a new message. This is the same one-card-per-message rule from Phase 2 applied to wiki sections.

   **Pick the question shape based on page content:**
   - **Code-heavy section:** predict output, fix a broken snippet, trace execution order
   - **Concept section:** compare/contrast, explain consequences of skipping, apply to a scenario
   - **List/reference section:** recall key items, explain rationale, identify which item applies

   **Ground the question in a concrete scenario with code, not an abstract prompt.** Show a real snippet or plausible work scenario and ask what happens, what changes, what breaks, or what the output is. Example contrast:
   - Weak: *"What's the difference between `index_by` and `index_with`?"*
   - Strong: *"Given `users = User.where(active: true).limit(3)` with ids 7, 12, 19 — what's the shape of `users.index_by(&:id)`? Write it out."*

   **When the question expects a code answer, anchor the expected shape:** state explicitly that a rough outline is fine and give a one-line example of the shape you'd accept (e.g., "Sketch the YAML — `key: value` form is enough.").

   **Tune difficulty by `review_interval`:** short (1-3d) → gentle recall; medium (4-14d) → standard application; long (15+d) → harder applied or "teach it back".

4. **Ask one section question, then wait for the developer's answer before asking the next.** One question per message — no batching.
5. **Evaluate each answer** as it comes in: 1-2 sentences of feedback and a per-section rating (1-4), then move to the next section's question (or, after the last section, to the rating breakdown). Assign page rating = rounded mean (round half-down). Score code answers on structural correctness, not literal completeness. **On a weak section answer, apply Socratic Never-Reveal** — recover via smaller guiding questions until the developer produces the missing piece, then rate; do not read the section content back at them.
6. State rating breakdown and apply:
   > Section A: Good · Section B: Hard → page rated **Hard (2)**. Applying.
7. Run `scripts/wiki-reschedule wiki/<path>.md <rating> --probed "<Section A>" --probed "<Section B>"` — repeat the `--probed` flag once per section (heading names may contain commas, so they are never comma-joined into one flag).
8. Confirm: `Rated **Hard (2)** — next review in 3 days (2026-04-22)`
9. **Open in browser** using the "Show in browser" flow from `references/wiki-write-protocol.md`. Say:
   > Opened in the browser — take your time reading. Say "next" when done, or "discuss" / "walkthrough" to dig in.
10. **Wait for explicit "next" / "done" before advancing.** Hard pause — do not auto-advance.
11. After all entries reviewed (or "done with wiki"), go to Phase 4.

**Wiki scheduling algorithm** (`scripts/wiki-reschedule`, source `scripts/wiki/reschedule.py`):**

| Rating | Formula | Min |
|--------|---------|-----|
| Again (1) | reset to 1 | — |
| Hard (2) | interval × 1.2 | 3 |
| Good (3) | interval × 2.5 | — |
| Easy (4) | interval × 4.0 | — |

**Mid-review actions:**
- "next" / "next wiki" — Advance to the next entry
- "discuss" / "tell me more" — Explain in depth
- "walkthrough" / "go deeper" — Chain into `/study-walkthrough`, then return
- "skip" — Skip without rating
- "done with wiki" / "skip wiki" — End wiki review, go to Phase 4

**Track wiki review data** internally for the session log:
- Wiki entries reviewed, ratings given, entries skipped

### Phase 4: Session Summary (1 message)

> **Session complete** — 12 cards in 11 minutes
> Accuracy: 83% | Streak: 5 days
>
> Weak areas: Deck B (2 lapses), Deck C (1 lapse)

### Phase 5: Session Log & Post-Session

**Write session log** — append to `logs/<MM>/<YYYY-MM-DD>.md` (create if doesn't exist):

```markdown
## Session N — Study (HH:MM)
- **Wiki reviewed:** 2 entries (Good ×1, Easy ×1)
  - [[architecture/event-sourcing]] → Good (3), next: 2026-04-21
  - [[architecture/cqrs]] → Easy (4), next: 2026-05-01
- **Cards reviewed:** 12 (+3 intra-day repeats)
- **Accuracy:** 83%
- **Lapses:** event sourcing (Again), CQRS (Hard)
- **Duration:** 11 min
- **Surprising:** <one card/concept the developer thought they knew but lapsed on, or vice versa — skip if nothing stood out>
- **Heuristic:** <one sentence a future study session in this area should read first — skip if none surfaced>
```

The `Surprising` and `Heuristic` fields are optional on `/study` (unlike `/study-walkthrough` where they're mandatory in Learning cadence). Write them only when the session actually produced a surprise or a generalizable rule — a routine clean-accuracy session doesn't need them. When present, they compound across sessions and feed `/progress` and `/reflect`.

Omit the **Wiki reviewed** line if no wiki entries were reviewed in this session.

**Lapse names are plain text, never wikilinks.** Write the card's topic name directly (e.g., "event sourcing"), not `[[architecture/event-sourcing]]`. Lapses refer to flashcard topics, which may not have wiki pages — linking them creates broken wikilinks.

**Push reviews to AnkiWeb.** After the session log, run `scripts/anki-sync sync` silently to push this session's reviews and any card changes. One-line confirm only if it moved something (e.g. `Anki sync: pushed 12 reviews.`); on failure, a one-line note — never re-run automatically or block the wrap-up.

**Wiki review entries use bare wikilinks, never backticked.** Write `[[architecture/event-sourcing]]` not `` `[[architecture/event-sourcing]]` ``. Backticks prevent Obsidian from rendering clickable links.

**Repeated lapse detection:** Read recent session logs to detect cross-session repeat lapses. If a topic has lapsed 3+ times across the past 7 days and has no wiki page, recommend `/study-walkthrough <topic>` — but keep the recommendation to a single sentence. Do not print the supporting log excerpts or per-session breakdowns.

**Post-session offers:**
- `/study-walkthrough <topic>` for struggling areas — "You had 2 lapses on event sourcing. Want to deepen that with /study-walkthrough?"
- `/study-flashcard` to create cards for gaps discovered during session
- `/study-walkthrough --write <topic>` to create a reference page for a topic you struggled with
- Revisit a due wiki page from Phase 1's list with `/study-walkthrough`

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

### "actually, your last explanation was wrong" / correction mid-feedback

**Correction Primitive.** If the developer corrects an explanation you gave in the feedback for a previous card (not the card itself), do not argue or layer a second explanation on top. Acknowledge in one line ("Got it — the correct answer is X"), re-state the correction cleanly, and carry the corrected version forward for any later card on the same topic. If a card whose feedback was wrong has already been rated, do not silently re-rate it — offer: "I gave you bad feedback on card N. Want me to reschedule it as Again/Hard so you see it again soon?" Let the developer decide.

### "split" / "this card is too big"

Show current card. Developer identifies distinct concepts. Draft focused cards for each. Create new cards, delete original (or ask if the original is worth keeping in a narrower form). Resume.

**Inherit the original's schedule — never reset split cards to fresh.** When the original card already had review history (state `review`/`relearning`, a non-zero interval), the new cards must keep that maturity. Pass `inheritFrom: <original card id>` to **every** `create_card` call in the split so each new card copies the original's FSRS block (due, stability, difficulty, reps, lapses, state, lastReview, interval, maturity). Splitting is a re-phrasing of material the developer already knows at that interval — fresh cards would wrongly resurface it immediately. Do this **before** deleting the original (you need its id, and the inheritance reads the live row). After creating, state the inherited interval from each card's returned `interval`/`due` (e.g. "4 cards created, each inheriting the original's schedule — next due 2026-09-11"). The same rule applies whenever a new card is derived from an existing one, not only on explicit "split". Do not offer to fake a review or seed an arbitrary interval — `inheritFrom` is the supported, exact mechanism.

### "delete" / "drop this card" / "this card is useless"

Delete the card via `delete_card`. Do not counter-offer suspend — adding new cards is cheap; preserving review history on a bad card is not valuable. One-line confirm is fine for borderline cases ("delete permanently — sure?"), but on an unambiguous instruction just act. Resume.

### "reschedule" / "show this later" / "not now"

Ask when to resurface. Rate accordingly to push FSRS scheduling out. Resume.

### "skip"

Call `skip_card`, advance to next.

### "done" / "stop" / "end"

Go to Phase 4 (Session Summary) with whatever was reviewed.

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
- Link lapses to wiki pages when they exist

**Never:**
- Show the answer before the developer attempts a response
- Reveal the back to fill a gap on a weak answer — decompose into a smaller question instead (explicit developer request excepted)
- Create cards automatically
- Batch multiple cards in one message
- Batch multiple questions in one message — wiki section questions are asked strictly one at a time (never "take them in order")
- Ask the developer which wiki page to open — review due pages automatically, most-due first
- Ignore mid-session requests
- Skip the session log
