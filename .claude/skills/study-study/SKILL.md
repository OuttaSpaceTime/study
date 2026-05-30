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

**At any point** during the session, the developer can say "show in Obsidian" to launch Obsidian and view wiki pages related to the current card. Follow the "Show in Obsidian" flow in `references/wiki-write-protocol.md`.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- ONE card per message, under 150-200 words of prose. Pause for discussion.
- The developer can interrupt at any point — see Mid-Session Actions below.
- Start each card with its position: `Card 3/12 — [Deck Name]`
- After feedback, immediately advance to the next card — do not wait for "next".

## Output Discipline

**Run all lookups silently.** `scripts/srs-pressure`, `scripts/wiki-due`, `scripts/wiki-probes`, `Read` of wiki pages or the index, `mcp__flashcard-mcp__*` calls — these execute without preamble narration ("Starting Phase 1…", "Let me check…") and without any echoing of their stdout, JSON, or file contents into chat. The chat shows only synthesized output: the pressure verdict line, the wiki-due numbered list, the question, the rating, the next prompt. If a script exits non-zero or errors, surface a one-line summary, not the stderr blob. This generalizes the existing "read logs, never tail" rule to every tool the skill calls.

## Anti-Overload Principle

- Default to conservative session sizes (5 new + 15 review cards)
- If the developer says "fewer", "less", "short session" — immediately call `adjust_session`
- Never auto-generate cards. Only suggest when a clear gap is observed.
- If the developer has studied today already, acknowledge it
- Show "Session complete" when queue is exhausted — do not pull more cards

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

**Two script calls, nothing else.** Run `scripts/srs-pressure --human` and `scripts/wiki-due` — these are the only lookups in Phase 1. No log reads, no index reads, no extra Bash calls.

`scripts/srs-pressure --human` is the **single source of truth** for flashcard due counts and the pressure verdict. Do **not** call `mcp__flashcard-mcp__get_due_cards` for pressure counts — it caps at 30 and underreports.

`scripts/wiki-due --human` returns the full formatted list of due wiki entries. Print it directly in the opening message — this is informational only, wiki review happens after flashcards (Phase 3).

Emit one opening message with the pressure verdict, the wiki due list, then **immediately start Phase 2 (flashcard loop)** — no confirmation gate, no "ready?", no "say open N".

Example when burdened:

> **Pressure:** burdened — 48 flashcards due, 23 wiki pages due. `maxNewCards: 0`.
>
> **Wiki due (23):**
> 1. [[programming-languages/compilers-and-interpreters]] — due 2026-05-12 (interval: 4d)
> 2. [[llm/kv-cache]] — due 2026-05-13 (interval: 6d)
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

The warn-threshold cap exists because over-adding under load is the recurring failure mode (see `feedback_srs_over_adding`). The pressure script's `flashcards due` count is the trigger — not the wiki/new-today axes. The developer can override explicitly ("include new cards anyway") — pass their requested number and note the override in the session log.

**Surface the cap in the opening line of Phase 2** so the developer never wonders where the new cards went. Example:

> Starting session — 4 due (3 relearning + 1 review), 18 new held back (pressure: warn). `maxNewCards: 0`.

If cards span multiple decks, **interleave** them — don't exhaust one deck before starting the next. Mix topics to strengthen cross-domain connections.

Then loop:

1. **Call `get_next_card`** — if null, go to Phase 3 (Wiki Review)
2. **Present the card front**, followed by a small italic footer listing mid-session actions:
   > *(discuss · edit · split · delete · reschedule · show in Obsidian)*
3. **Wait for the developer's answer**
3a. **Probe option for code-shaped cards.** When the card is code-shaped (git, Python, shell, SQL, HTTP, regex, algorithms) **and** the developer's answer is uncertain, partial, or asserts a specific output, offer one quick probe before evaluating: a `python -c` line, a `git` command, a `curl | jq`, a small unit assertion. The developer runs it and pastes the output. Compare to what they predicted. If prediction and output disagree, name the gap explicitly (`predicted X, got Y`) before rating — that gap is the rating signal, not a side note. If a probe surprises, persist it under `probes/<topic-slug>/YYYY-MM-DD-HHMM-<brief>.md` using `probes/_template.md` (Prediction / Command / Output / Takeaway). Skip the probe entirely for theory-only cards or when the developer's recall was clearly solid — probing in that case is ceremony.
4. **Evaluate the answer** against the card back (and the probe output, when one was run):
   - `Again (1)`: Wrong or fundamentally misses the concept
   - `Hard (2)`: Mostly correct but significant gaps
   - `Good (3)`: Correct answer with reasonable detail
   - `Easy (4)`: Perfect, immediate recall
5. **Show feedback** — brief, constructive:
   - Reveal the card back
   - State what was correct and what was missing (1-2 sentences)
   - State the rating: "Rated: **Good (3)**"
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
   - One-liner reminder: *(harder/easier · discuss · edit · split · delete · show in Obsidian)*
6. **Call `submit_review`** with the rating
7. **Advance** — call `get_next_card` and present the next card in the same message. Only advance if no quality issue was flagged (or developer resolved/skipped it).

**Track session data** internally for the log:
- Cards reviewed, ratings given, lapses (Again ratings), start time

### Phase 3: Wiki Review (after flashcards)

When the flashcard queue is exhausted, offer wiki review using the list already shown in Phase 1:

> **Flashcards done.** 23 wiki pages are due — want to review some? Say "open 1" (or a number), "open <slug>", or "skip wiki" to go straight to the summary.

If the developer says "skip wiki" or there were no due wiki entries, go to Phase 4.

**Review loop for each entry:**

1. Developer says "open 1" (or "open git-restore", or "next")
2. Read the wiki page. Present a brief summary: title, sections, depth, current interval — but do NOT open Obsidian yet.
2a. **Surface linked probes (if any):** Run `scripts/wiki-probes <wiki-path>`. If probes exist, list them with path and Takeaway one-liner. Offer: "Want to re-run one as a recall check before I ask the section questions?" Skip silently if none.
3. **Pick sections to probe — rotation via `last_probed`:**

   Read `probe_sections` and `last_probed` from the page's YAML frontmatter. `last_probed` is an ordered queue (oldest first); treat as `probe_sections` order if empty.

   Choose `n = min(len(probe_sections), 3)` sections — the first `n` from the queue. Ask **one focused question per section**, cap 3 total.

   **Pick the question shape based on page content:**
   - **Code-heavy section:** predict output, fix a broken snippet, trace execution order
   - **Concept section:** compare/contrast, explain consequences of skipping, apply to a scenario
   - **List/reference section:** recall key items, explain rationale, identify which item applies

   **Ground the question in a concrete scenario with code, not an abstract prompt.** Show a real snippet or plausible work scenario and ask what happens, what changes, what breaks, or what the output is. Example contrast:
   - Weak: *"What's the difference between `index_by` and `index_with`?"*
   - Strong: *"Given `users = User.where(active: true).limit(3)` with ids 7, 12, 19 — what's the shape of `users.index_by(&:id)`? Write it out."*

   **When the question expects a code answer, anchor the expected shape:** state explicitly that a rough outline is fine and give a one-line example of the shape you'd accept (e.g., "Sketch the YAML — `key: value` form is enough.").

   **Tune difficulty by `review_interval`:** short (1-3d) → gentle recall; medium (4-14d) → standard application; long (15+d) → harder applied or "teach it back".

4. **Wait for the developer's answer to each question in turn.**
5. **Evaluate each answer** with 1-2 sentences of feedback and a per-section rating (1-4). Assign page rating = rounded mean (round half-down). Score code answers on structural correctness, not literal completeness.
6. State rating breakdown and apply:
   > Section A: Good · Section B: Hard → page rated **Hard (2)**. Applying.
7. Run `scripts/wiki-reschedule wiki/<path>.md <rating> --probed "<Section A>,<Section B>"`.
8. Confirm: `Rated **Hard (2)** — next review in 3 days (2026-04-22)`
9. **Open Obsidian** using the "Show in Obsidian" flow from `references/wiki-write-protocol.md`. Say:
   > Opened in Obsidian — take your time reading. Say "next" when done, or "discuss" / "walkthrough" to dig in.
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
- **Cards reviewed:** 12
- **Accuracy:** 83%
- **Lapses:** event sourcing (Again), CQRS (Hard)
- **Duration:** 11 min
- **Surprising:** <one card/concept the developer thought they knew but lapsed on, or vice versa — skip if nothing stood out>
- **Heuristic:** <one sentence a future study session in this area should read first — skip if none surfaced>
```

The `Surprising` and `Heuristic` fields are optional on `/study` (unlike `/study-walkthrough` where they're mandatory in Learning cadence). Write them only when the session actually produced a surprise or a generalizable rule — a routine clean-accuracy session doesn't need them. When present, they compound across sessions and feed `/progress` and `/reflect`.

Omit the **Wiki reviewed** line if no wiki entries were reviewed in this session.

**Lapse names are plain text, never wikilinks.** Write the card's topic name directly (e.g., "event sourcing"), not `[[architecture/event-sourcing]]`. Lapses refer to flashcard topics, which may not have wiki pages — linking them creates broken wikilinks.

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

### "actually, your last explanation was wrong" / correction mid-feedback

**Correction Primitive.** If the developer corrects an explanation you gave in the feedback for a previous card (not the card itself), do not argue or layer a second explanation on top. Acknowledge in one line ("Got it — the correct answer is X"), re-state the correction cleanly, and carry the corrected version forward for any later card on the same topic. If a card whose feedback was wrong has already been rated, do not silently re-rate it — offer: "I gave you bad feedback on card N. Want me to reschedule it as Again/Hard so you see it again soon?" Let the developer decide.

### "split" / "this card is too big"

Show current card. Developer identifies distinct concepts. Draft focused cards for each. Create new cards, delete original (or ask if the original is worth keeping in a narrower form). Resume.

### "delete" / "drop this card" / "this card is useless"

Delete the card via `delete_card`. Do not counter-offer suspend — adding new cards is cheap; preserving review history on a bad card is not valuable. One-line confirm is fine for borderline cases ("delete permanently — sure?"), but on an unambiguous instruction just act. Resume.

### "reschedule" / "show this later" / "not now"

Ask when to resurface. Rate accordingly to push FSRS scheduling out. Resume.

### "skip"

Call `skip_card`, advance to next.

### "done" / "stop" / "end"

Go to Phase 3 (Session Summary) with whatever was reviewed.

### "fewer" / "less" / "shorten"

Call `adjust_session`. Confirm reduction. Continue.

### "add" / "new card"

Chain to `/study-flashcard` with current deck. After creation, resume.

### "show in Obsidian" / "open in Obsidian"

Follow the "Show in Obsidian" flow from `references/wiki-write-protocol.md`. If a wiki page exists for the current card's topic, open it. If not, offer to create one. Resume session after.

---

## Rating Override

If developer says "actually harder" or "actually easier" after feedback, acknowledge and adjust. The already-submitted rating is persisted; factor self-assessment into future evaluations of this card.

## Guardrails

**Always:**
- Reference actual codebase code when discussing card concepts
- Give the developer a chance to answer before revealing the back
- Respect every mid-session action immediately
- Write session log at the end of every session
- Link lapses to wiki pages when they exist

**Never:**
- Show the answer before the developer attempts a response
- Create cards automatically
- Batch multiple cards in one message
- Ignore mid-session requests
- Skip the session log
