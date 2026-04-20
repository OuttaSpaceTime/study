---
name: study
description: "Interactive spaced repetition study session with Claude as evaluator. Reviews due flashcards, rates answers, logs sessions, and supports mid-session actions: discuss, walkthrough, edit, split, reschedule, pause. Trigger keywords: study, review cards, flashcards, spaced repetition."
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

### Phase 1: Status Check & Wiki Revisit Prompt (1 message)

Call MCP tools: `get_stats`, `get_due_cards`, `list_decks`.

Resolve the **session category** first (see Category section). Once known, pass `--category <cat>` to every `scripts/wiki-due` call in this skill so counts and lists are scoped consistently.

Run `scripts/wiki-due --count --category <cat>` to get the number of wiki entries due for review **in the chosen category**.

**Macro analytics:** Read recent entries from `logs/` (last 7 days). Compute:
- Cards reviewed this week, average accuracy, lapse trend (improving or declining)
- Topics with repeated lapses (same card lapsed 2+ times across sessions)

**Wiki revisit check:** Read `wiki/.wiki-index.json`, find pages where `last_deepened` is >30 days ago or `depth` is 1. If any exist, surface 1-2:
> Wiki page [[architecture/event-sourcing]] hasn't been revisited in 45 days (depth: 1). Consider `/study-walkthrough` to deepen it.

Present a brief status (include wiki due count when > 0):

> You have **2 wiki entries due for review** and **8 cards due** (3 in Deck A, 5 in Deck B). Your streak is 4 days.
> This week: 34 cards, 81% accuracy (↑ from 76% last week). Repeated lapses on: event sourcing (3x).
> We'll start with wiki review, then move to flashcards. Ready?

If no cards are due but wiki entries are:

> No cards due today, but **2 wiki entries** are ready for review. Ready?

If nothing is due:

> No cards or wiki entries due today — you're all caught up!
> Want to: add new cards, revisit a stale wiki page with /study-walkthrough, or call it a day?

Wait for developer confirmation before starting.

### Phase 2: Wiki Review

Run `scripts/wiki-due --category <cat>` to get the full list of due wiki entries in the session's category.

If no wiki entries are due, skip silently to Phase 3 (Flashcard Study Loop).

Present the due entries as a numbered list:

> **Wiki review:** 2 entries due.
> 1. [[git/git-restore]] — git, version-control (due: 2026-04-12, interval: 3d)
> 2. [[architecture/event-sourcing]] — architecture (due: 2026-04-07, interval: 7d)
>
> Say "open 1" to start, or "skip wiki" to go straight to flashcards.

**Review loop for each entry:**

1. Developer says "open 1" (or "open git-restore", or "next")
2. Read the wiki page. Present a brief summary: title, sections, depth, when created, current interval — but do NOT open Obsidian yet.
3. **Pick sections to probe — rotation via `last_probed`:**

   Read `probe_sections` and `last_probed` from the index entry. `last_probed` is an ordered queue (oldest first); on the very first review it may be empty, treat as `probe_sections` order.

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
5. **Evaluate each answer** with brief feedback (1-2 sentences) and a per-section rating (1-4). After all picked sections are answered, **assign the page rating = worst-of the per-section evaluations** — if any section was Again, the page is Again; if the worst was Hard, the page is Hard. Conservative by design: one shaky section drops the whole page.
6. **Open Obsidian:** Open the page in Obsidian using the "Show in Obsidian" flow from `references/wiki-write-protocol.md`. Never display the page content in chat — the developer reads it in Obsidian.
7. State the computed rating with the per-section breakdown, and offer an override:
   > Section A: Good · Section B: Hard · Section C: Good → page rated **Hard (2)**.
   > Say "actually good" / "actually again" to override, otherwise I'll apply this.
8. If the developer overrides, use their rating; otherwise use the computed one.
9. Run `scripts/wiki-reschedule <path> <rating> --probed "<Section A>,<Section B>"` — computes the new interval, rewrites frontmatter (including rotating `last_probed`), and re-indexes. Pass the exact section headings you probed, comma-separated.
10. Confirm rating and next review date: `Rated **Hard (2)** — next review in 3 days (2026-04-22)`
11. **Pause here.** Do NOT auto-advance. Wait for the developer to say "go on to next wiki", "next wiki", or "next" before proceeding. This gives them room to ask follow-up questions, request a deeper walkthrough, or discuss the entry.
12. After all entries reviewed (or developer says "done with wiki"), proceed to Phase 3

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
2. **Present the card front**
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
   - One-liner reminder: *(harder/easier · discuss · edit · split · pause · show in Obsidian)*
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
```

Omit the **Wiki reviewed** line if no wiki entries were reviewed in this session.

**Lapse names are plain text, never wikilinks.** Write the card's topic name directly (e.g., "event sourcing"), not `[[architecture/event-sourcing]]`. Lapses refer to flashcard topics, which may not have wiki pages — linking them creates broken wikilinks.

**Wiki review entries use bare wikilinks, never backticked.** Write `[[architecture/event-sourcing]]` not `` `[[architecture/event-sourcing]]` ``. Backticks prevent Obsidian from rendering clickable links.

**Repeated lapse detection:** Check session logs from the past 7 days. If a topic has lapsed 3+ times across sessions and has no wiki page, **proactively recommend** creating one:
> "Event sourcing has lapsed 3 times this week and has no wiki page. This pattern suggests a gap that flashcards alone aren't closing. I'd recommend `/study-walkthrough event sourcing` to build a deeper understanding and write a wiki page."

This is stronger than "offer" — it's a data-driven recommendation. The developer still decides.

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

### "split" / "this card is too big"

Show current card. Developer identifies distinct concepts. Draft focused cards for each. Create new cards, suspend original. Resume.

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
