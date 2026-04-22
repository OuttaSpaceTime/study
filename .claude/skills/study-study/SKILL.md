---
name: study
description: "Interactive spaced repetition study session with Claude as evaluator. Reviews due flashcards, rates answers, logs sessions, and supports mid-session actions: discuss, walkthrough, edit, split, delete, reschedule, pause. Trigger keywords: study, review cards, flashcards, spaced repetition."
user_invocable: true
---

# /study — Interactive Spaced Repetition Study Session

## Core Guarantee

The developer leaves each session with reinforced knowledge, accurate scheduling, and awareness of weak areas. Claude evaluates answers — no self-rating required. The developer can interrupt any card to discuss, edit, split, reschedule, pause, or chain into a walkthrough. The session adapts to the developer, not the other way around.

## Wiki Integration

This skill logs session performance to `logs/YYYY-MM-DD.md`. It can also trigger wiki writes when gaps are discovered during study.

**At any point** during the session, the developer can say "show in Obsidian" to launch Obsidian and view wiki pages related to the current card. Follow the "Show in Obsidian" flow in `references/wiki-write-protocol.md`.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for shared interactive principles.

- ONE card per message, under 150-200 words of prose. Pause for discussion.
- The developer can interrupt at any point — see Mid-Session Actions below.
- Start each card with its position: `Card 3/12 — [Deck Name]`
- After feedback, immediately advance to the next card — do not wait for "next".

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
/study                    — Start a default study session (prompts for category)
/study -c work|personal   — Scope the session to one category (skips the prompt)
/study <deck-name>        — Focus on a specific deck
/study --short            — Short session (5 cards max)
/study add                — Create new flashcards (chain to /study-flashcard)
/study add <deck-name>    — Create flashcards for a specific deck
```

## Category

Every study session is scoped to a single category. Follow `references/category-policy.md` to resolve it — prompt happens after the Phase 1 status summary when no `-c` flag was passed. The resolved value flows into `start_session({ category })` and every `scripts/wiki-due --category <cat>` call. Mid-session, `focus work` / `focus personal` narrows via `adjust_session({ focusCategory })` — see Mid-Session Actions.

---

## Study Session Flow

### Phase 1: Pressure Check & Status (1 message)

**Burdened-state preflight — always first.** Run `scripts/srs-pressure --human` and surface its verdict as the opening line of the first message. State explicitly whether the developer is within a burdened state or not before anything else. The script is the **single source of truth** for due counts and per-deck breakdown — it fetches accurate counts via the flashcard-mcp CLI.

Do **not** call `mcp__flashcard-mcp__get_due_cards` for pressure counts — it caps at 30 and underreports. The script's per-deck breakdown replaces a separate `list_decks` call for status purposes. You may still call `get_stats` for streak/recent-sessions context, and `list_decks` is fine only if you later need deck IDs for `start_session`.

Resolve the **session category** (see Category section). Once known, pass `--category <cat>` to every `scripts/wiki-due` call in this skill so counts and lists are scoped consistently.

Run `scripts/wiki-due --count --category <cat>` to get the number of wiki entries due for review **in the chosen category**.

**Read `logs/` for analysis, never tail into chat.** You may read recent log entries to compute macro analytics (weekly accuracy, lapse trends, repeated-lapse topics) and use them to shape recommendations (e.g., suggest a walkthrough for a repeatedly-lapsed topic). But do **not** print log excerpts, weekly stats dumps, or lapse tables into the chat. Surface only a single-line takeaway when it drives a concrete suggestion — otherwise stay silent. The pressure-check verdict remains the only load signal shown at the top of Phase 1.

**Wiki revisit check:** Read `wiki/.wiki-index.json`, find pages where `last_deepened` is >30 days ago or `depth` is 1. If any exist, surface 1-2:
> Wiki page [[architecture/event-sourcing]] hasn't been revisited in 45 days (depth: 1). Consider `/study-walkthrough` to deepen it.

Present the pressure verdict as a single opening line, then **proceed directly into Phase 2 (Wiki Review) in the same message** — do not ask "Ready?" and do not wait for confirmation. The preflight verdict is the only preamble; wiki review starts immediately after it.

> **Pressure:** not burdened (42 due, within capacity). 2 wiki entries due, 8 cards due. Starting with wiki.
>
> **Wiki review:** 2 entries due.
> 1. [[git/git-restore]] — …
> 2. [[architecture/event-sourcing]] — …
>
> Say "open 1" to start, or "skip wiki" to go straight to flashcards.

If no wiki entries are due, state that in the opening line and go straight into Phase 3 (flashcard loop) — still no confirmation gate.

If nothing is due anywhere:

> No cards or wiki entries due today — you're all caught up!
> Want to: add new cards, revisit a stale wiki page with /study-walkthrough, or call it a day?

### Phase 2: Wiki Review

Run `scripts/wiki-due --category <cat>` to get the full list of due wiki entries in the session's category. This runs as part of the Phase 1 message — the numbered list (shown in Phase 1) is the entry point into this phase. If no wiki entries are due, skip silently to Phase 3.

Listing format (emitted from Phase 1):

> **Wiki review:** 2 entries due.
> 1. [[git/git-restore]] — git, version-control (due: 2026-04-12, interval: 3d)
> 2. [[architecture/event-sourcing]] — architecture (due: 2026-04-07, interval: 7d)
>
> Say "open 1" to start, or "skip wiki" to go straight to flashcards.

**Review loop for each entry:**

1. Developer says "open 1" (or "open git-restore", or "next")
2. Read the wiki page. Present a brief summary: title, sections, depth, when created, current interval — but do NOT open Obsidian yet.
2a. **Surface linked probes (if any):** Run `scripts/wiki-probes <wiki-path>` (e.g. `scripts/wiki-probes architecture/event-sourcing`). If probes exist, list them with path and Takeaway one-liner. Offer: "Want to re-run one as a recall check before I ask the section questions?" A probe the developer can no longer predict the output of is a real gap. Skip silently if the script returns an empty list.
3. **Pick sections to probe — rotation via `last_probed`:**

   Read `probe_sections` and `last_probed` from the page's YAML frontmatter (already loaded in step 2 — do not re-parse the index). `last_probed` is an ordered queue (oldest first); on the very first review it may be empty, treat as `probe_sections` order.

   Choose `n = min(len(probe_sections), 3)` sections. Pick the first `n` from the queue — these are the longest-unprobed. Ask **one focused question per picked section** — do NOT ask multiple questions per section. This keeps the total at 1-3 questions regardless of page size.

   **Pick the question shape based on page content:**
   - **Code-heavy section:** predict output, fix a broken snippet, write a function that does X, trace execution order
   - **Concept section:** compare/contrast with alternative ("when X over Y?"), explain consequences of skipping, apply to a scenario, define in own words
   - **List/reference section:** recall key items, explain rationale behind an item, identify which item applies to a scenario

   **Tune difficulty based on the page's last rating (from frontmatter `review_interval`):**
   - **Short interval (1-3 days) — recent lapse:** gentle recall. "What is X?" / "What does this command do?"
   - **Medium interval (4-14 days):** standard application question. "When would you use X?" / "What happens if you omit this?"
   - **Long interval (15+ days) — strong recall history:** harder applied question. "Given this scenario, how would you combine X and Y?" / "Teach this back to me — what's the mental model?"

   Never turn this into a quiz — one question per probed section, cap 3.

4. **Wait for the developer's answer to each question in turn.** Ask one, wait, evaluate, then move to the next probed section.
5. **Evaluate each answer** with brief feedback (1-2 sentences) and a per-section rating (1-4). After all picked sections are answered, **assign the page rating = rounded mean of the per-section evaluations** (round half-down toward the weaker rating — e.g. Good+Hard → Hard, Good+Good+Hard → Good). This surfaces a reasonable middle ground rather than letting one shaky section drop the whole page.
6. State the computed rating with the per-section breakdown, then apply it directly — do not ask the developer to confirm or override:
   > Section A: Good · Section B: Hard · Section C: Good → page rated **Good (3)**. Applying.
7. Run `scripts/wiki-reschedule wiki/<path>.md <rating> --probed "<Section A>,<Section B>"` (e.g. `scripts/wiki-reschedule wiki/git/git-restore.md 2 --probed "..."`) — computes the new interval, rewrites frontmatter (including rotating `last_probed`), and re-indexes. The path is filesystem-relative with the `wiki/` prefix and `.md` suffix — unlike `scripts/wiki-probes`, which takes the bare wiki-root path. Pass the exact section headings you probed, comma-separated.
8. Confirm rating and next review date: `Rated **Hard (2)** — next review in 3 days (2026-04-22)`
9. **Open Obsidian at the end:** Open the page in Obsidian using the "Show in Obsidian" flow from `references/wiki-write-protocol.md`. Never display the page content in chat — the developer reads it in Obsidian. Then say:
   > Opened in Obsidian — take your time reading. Say "next" / "go on to next wiki" when done, or "discuss" / "walkthrough" to dig in.
10. **Wait for the developer to finish reading.** Do NOT auto-advance. Only proceed after the developer explicitly says "next", "go on to next wiki", or similar. This is a hard pause — never assume they're done just because time has passed or because the previous tool call returned. Follow-up questions, discussion, or a deeper walkthrough are all valid uses of this pause.
11. After all entries reviewed (or developer says "done with wiki"), proceed to Phase 3

**Wiki scheduling algorithm** is implemented in `scripts/wiki-reschedule` (source: `scripts/wiki/reschedule.py`). The rating-to-interval mapping:

| Rating | Formula | Min |
|--------|---------|-----|
| Again (1) | reset to 1 | — |
| Hard (2) | interval × 1.2 | 3 |
| Good (3) | interval × 2.5 | — |
| Easy (4) | interval × 4.0 | — |

Initial values are set when a wiki page is created: `review_interval: 3`, `next_review: created + 3 days`.

**Mid-review actions:**
- "go on to next wiki" / "next wiki" / "next" — Advance to the next wiki entry (required after each rated entry)
- "discuss" / "tell me more" — Explain the wiki page content in depth
- "walkthrough" / "go deeper" — Chain into `/study-walkthrough` on this topic, then return to wiki review
- "skip" — Skip this entry without rating (next_review unchanged)
- "skip wiki" / "done with wiki" — End wiki review, proceed to flashcards

**Track wiki review data** internally for the session log:
- Wiki entries reviewed, ratings given, entries skipped

### Phase 3: Study Loop (1 card per message)

Call `start_session` with appropriate config, including **`category`** (the session category captured in Phase 1). If cards span multiple decks, **interleave** them — don't exhaust one deck before starting the next. Mix topics to strengthen cross-domain connections.

Then loop:

1. **Call `get_next_card`** — if null, go to Phase 4
2. **Present the card front**, followed by a small italic footer listing mid-session actions:
   > *(discuss · edit · split · delete · reschedule · pause · show in Obsidian)*
3. **Wait for the developer's answer**
4. **Evaluate the answer** against the card back:
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
     - **Mismatched Q/A:** front asks "what" but back explains "why", or vice versa
     - Do NOT flag cards that are intentionally minimal — simple recall cards with precise, correct backs are fine.
     - **When a quality issue is detected: stop advancing.** Explicitly describe the problem and ask the developer to fix it before continuing. Example: "This card's front is ambiguous — it could mean X or Y. Want to edit it to be more specific, or split it?" Wait for the developer to edit, split, or explicitly say "skip" before moving on.
   - **Generation prompt** (on Good/Easy cards, ~1 in 4 cards): Ask the developer to generate their own example or analogy: "Can you give me a real-world scenario where this applies?" This strengthens encoding. Keep it brief — one sentence is enough.
   - One-liner reminder: *(harder/easier · discuss · edit · split · delete · pause · show in Obsidian)*
6. **Call `submit_review`** with the rating
7. **Advance** — call `get_next_card` and present the next card in the same message. Only advance if no quality issue was flagged (or developer resolved/skipped it).

**Track session data** internally for the log:
- Cards reviewed, ratings given, lapses (Again ratings), start time

### Phase 4: Session Summary (1 message)

> **Session complete** — 12 cards in 11 minutes
> Accuracy: 83% | Streak: 5 days
>
> Weak areas: Deck B (2 lapses), Deck C (1 lapse)

### Phase 5: Session Log & Post-Session

**Write session log** — append to `logs/YYYY-MM-DD.md` (create if doesn't exist):

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
- Revisit a stale wiki page (surfaced in Phase 1) with `/study-walkthrough`

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

### "pause" / "brb"

Note progress. Wait for "resume" or "done".

### "skip"

Call `skip_card`, advance to next.

### "done" / "stop" / "end"

Go to Phase 3 (Session Summary) with whatever was reviewed.

### "fewer" / "less" / "shorten"

Call `adjust_session`. Confirm reduction. Continue.

### "focus work" / "focus personal"

Narrow the current session to one category mid-flight. Call `adjust_session({ focusCategory: "work" | "personal" })`. Confirm the narrowing and resume with the filtered queue. Use when the developer realizes mid-session that they want to ignore cards outside the current focus.

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
