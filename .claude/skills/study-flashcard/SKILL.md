---
name: study-flashcard
description: "Create SRS flashcards through an interactive walkthrough that checks against existing cards. Optionally writes a companion wiki page. Trigger keywords: create flashcard, add flashcard, new flashcard, make flashcard."
user_invocable: true
---

# Interactive Flashcard Creator

Create flashcards for the spaced repetition system through an interactive 4-checkpoint walkthrough. Every card is checked against existing cards before creation — no duplicates, no overload. Optionally writes a companion wiki page summarizing the flashcarded concepts.

**Core guarantee:** The developer understands every flashcard before it enters the SRS. If they cannot explain the concept back, the walkthrough continues. Every draft is checked against existing cards using semantic similarity.

## Wiki Integration

This skill can write companion wiki pages to `wiki/`. See `references/wiki-write-protocol.md` for the full "write wiki" flow, linking rules, and frontmatter spec. All wikilinks use absolute paths from wiki root (e.g., `[[javascript/closures]]` not `[[closures]]`).

**At any point** during the session, the developer can say "show in browser" to open wiki pages in the wiki-viewer app. Follow the "Show in browser" flow in the wiki-write-protocol.

## Session Rules

For additional shared interactive principles (scope, handling disagreement, non-interactive mode), see `~/.claude/skills/references/interactive-principles.md`.

- ONE concept per message, under 150-200 words of prose. Pause for discussion.
- If the developer already knows the topic well, compress Checkpoint 2 and move to drafting.
- Start each checkpoint with `Checkpoint X/4: <title>`.
- Pause after each checkpoint — ask whether to continue or discuss. Never auto-advance.
- At each checkpoint, blend guided and unguided modes.
- **Read silently, never cat.** Run `scripts/srs-pressure`, `scripts/wiki-search`, `mcp__flashcard-mcp__find_similar_cards`, and any `Read` calls without preamble narration and without echoing their stdout, JSON, or file contents into chat. The chat shows only synthesized output — the pressure verdict, similar-card warnings, draft cards, the next checkpoint prompt. See AGENTS.md "Skill Design Principles → Read silently, never cat."

## Correction Primitive

When the developer corrects a concept explanation or draft card mid-session:

- **Edit the draft in place**, do not append "actually, X". The running draft list is the artifact; if Checkpoint 3 already shows a bad front/back, rewrite it in the next message rather than adding a second version below it.
- If a correction invalidates a concept walked through in Checkpoint 2, mark any dependent drafts `[STALE — redraw]` and redo them before Checkpoint 4.
- If cards have already been created (mid-Checkpoint-4 corrections), call `update_card` to fix them rather than creating new variants. Never leave two near-duplicate cards in the deck because of a mid-session correction.

## Output Contract — Progress Footer (mandatory)

Every assistant message in this skill **must end with a progress footer as the LAST line**. No exceptions while the interactive flow is active — this includes clarifying questions, short acknowledgements, and messages that contain only code. A message without this footer is a contract violation.

**Format:**
- With steps: `Step 1/2 · Checkpoint 3/4 — Draft Review & Duplicate Check: similarity scan`
- Without steps: `Checkpoint 1/4 — Topic & Scope`

The footer is a single line, rendered verbatim, at the very bottom of the message — nothing after it.

**Exceptions:** Omit the footer only when the developer has explicitly opted out of the interactive flow — non-interactive subagent mode, or an explicit "just draft the cards" request.

## MCP Server Dependency

This skill requires the `flashcard-mcp` MCP server. Tools used: `find_similar_cards`, `create_card`, `list_decks`.

**Note:** Always use `find_similar_cards` for duplicate detection — it uses semantic similarity (Jaccard + cosine embeddings). `search_cards` is exact substring match only and is not suitable for duplicate checks.

## Invocation

```
/study-flashcard                          — Create flashcards (asks for topic and deck)
/study-flashcard <topic>                  — Create flashcards about a specific topic
/study-flashcard <topic> <deck-name>      — Create flashcards about a topic in a specific deck
/study-flashcard --from <url>             — Create flashcards from a URL (use WebFetch to retrieve content)
/study-flashcard <any text or paragraph>  — Extract key concepts from the provided text and create flashcards
```

When invoked with a block of text or URL, treat it as source material. The flashcards and wiki page capture only what was walked through and understood — not a raw dump.

## Preflight — SRS Pressure Check (MANDATORY, ALWAYS FIRST)

**Before Checkpoint 1. Before any tool call. Before any deck listing, similarity scan, wiki read, or drafting.** The first assistant message of this skill invocation must be the pressure-check output — nothing else.

Follow `references/srs-pressure-check.md` exactly. Summary:

1. Run `scripts/srs-pressure --human` — it fetches accurate counts via the flashcard-mcp CLI itself. Do **not** call `mcp__flashcard-mcp__get_due_cards` or `mcp__flashcard-mcp__list_decks` for pressure signals (`get_due_cards` caps at 30 and will underreport).
2. First message output:
   - `ok` → one line: `SRS pressure: ok — proceeding.`
   - `warn` / `pause` → full script output verbatim, then the gate question from the reference. Wait for an explicit answer before Checkpoint 1.
3. Progress footer for this message: `Preflight — SRS Pressure Check`.

**Contract:** skipping this step, folding it into Checkpoint 1, or running other tool calls before the verdict is a contract violation — same severity as omitting the progress footer. "Just one card" / "we already ran it earlier" / "the developer told me what they want" are **not** valid reasons to skip.

## Checkpoint Flow

### Checkpoint 1/4: Topic & Scope

(Preflight must be complete and — if warn/pause — explicitly acknowledged by the developer before starting this checkpoint.)

1. Call `list_decks` to show available decks. Ask which deck to target.
2. Determine what the developer wants to create flashcards about. Accept any of:
   - A topic, URL, file path, raw text, free text, or a concept from a recent session
   If raw text was provided at invocation, summarize: "I see 3 key concepts here: X, Y, Z. Which should we flashcard?"
3. Ask what the developer already knows about the topic — calibrate depth.
4. **Wiki check**: Read `wiki/.wiki-index.json` — check if a wiki page exists for this topic. If yes, show it:
   > `[[javascript/closures]]` exists. Your new flashcards will be linked to this page.
5. **Pre-check**: Call `find_similar_cards` with the topic text. If existing cards cover this area, show them:
   > "You already have 3 cards about this topic:
   > - *'Card 1'* (85% match)
   > Do you want to: add new cards that cover different aspects, edit existing cards, or skip?"
6. **Anti-overload gate:** Default: 2-3 cards. Developer can request more but push back gently.

**Scope decision tree:**
- Topic decomposes into >5 sub-concepts → suggest splitting into multiple sessions
- Developer already knows the topic well → skip to Checkpoint 3 with pre-written drafts
- Topic is trivial (single fact) → suggest a single card, skip the walkthrough

### Checkpoint 2/4: Core Concept Walkthrough

For each sub-concept that will become a flashcard:

1. Explain what it does and why it matters, with concrete codebase code when possible
2. **Concrete example/challenge (mandatory, every concept):** Ask the developer to actively produce something before moving on:
   - **Code concepts:** "What do you expect this outputs?" / "How would you write the code for that?" / "Here's a broken version — what's wrong?"
   - **Theory/architecture concepts:** "When would you choose this over X?" / "What breaks if you skip this step?" / "Explain why this matters in your own words"
   - Keep each challenge focused — one question, not a quiz. The answer reveals whether they truly understand the concept the flashcard will test.
3. Gap detected → pause and fill it. Understanding solid → move on.
4. As you walk through each concept, mentally draft the front/back — the walkthrough IS the drafting process
5. **Track related concepts** for wiki linking — note any existing wiki pages that come up

**Guided vs Unguided card decision** (decide per concept):
- Factual/definitional concept → **guided card** (Q&A flashcard)
- Skill/technique/practice → **unguided card** (exercise/task card)

### Checkpoint 3/4: Draft Review & Duplicate Check

For each card draft:

1. Present the draft (front, back, type, tags)
1a. **Atomicity check (front must have a single recall target):** Reject any front that asks for a superlative or judgment ("the single most effective", "the best way", "the right approach to X") or otherwise admits several defensible answers — there is nothing to grade against. Rewrite it to name the specific scenario or principle being tested before proceeding (e.g. "What's the single most effective technique for loose coupling?" → "Which design principle reduces coupling by depending on an abstraction instead of a concrete collaborator?"). This mirrors the *Non-atomic / opinion-bait front* flag in `/study`'s review-time quality check — catch it here so it never becomes a card.
2. **Semantic duplicate check**: Call `find_similar_cards` with the draft front text
   - >80% match: "Very similar card exists. Skip or rephrase?"
   - 50-80% match: "Related card exists. Your new card covers a different angle — proceed?"
   - No matches: "No similar cards found. This is new territory."
3. Ask the developer to explain the concept in their own words
4. Developer says "good", "next", "edit", or "skip" for each draft

### Checkpoint 4/4: Confirm, Create & Write Wiki

1. Present all approved drafts in a numbered list
2. Developer confirms: "Create these" or makes final edits
3. For each approved draft, call `create_card` with deckId, front, back, tags, and type
   - **Deriving from an existing card?** If these drafts are a split or rephrasing of a card that already has review history, pass `inheritFrom: <original card id>` on each `create_card` so the new cards copy the original's FSRS schedule (due, stability, interval, state, maturity) instead of resetting to fresh New cards. Read the original's id with `find_similar_cards`/`get_card` before creating, and delete the original only after the new cards are created. Brand-new concepts with no parent card omit `inheritFrom`.
4. Report results
4a. **Push to AnkiWeb:** run `scripts/anki-sync sync` silently so the new cards reach the phone right away. One-line confirm only if it moved something (e.g. `Anki sync: pushed 3 new cards.`); on failure, a one-line note — never block the session on it.
5. **Offer "write wiki"**: "Want to save a companion wiki page for these concepts?"
   - If yes, follow the full flow from `references/wiki-write-protocol.md`:
     - **Before drafting:** present a brief outline — title, proposed H2 sections with a one-line description each. Wait for confirmation or adjustment, then start writing from the top.
     - **Before drafting**, internalize that protocol's "Writing Style" section — no em-dashes anywhere, no prose-colons as clause connectors. Filename must equal `slugify(title)` exactly. Writing clean prose first time avoids multi-pass cleanup.
     - Draft a wiki page that goes beyond a thin summary, including context, examples, and the developer's own explanations from the walkthrough.
     - Include `flashcard_ids` in frontmatter with the IDs of created cards
     - **Required:** link to at least 2 related wiki pages via `[[absolute/path]]`. Search the index for connections. Companion pages must not be leaf nodes in the graph.
     - Resolve links, propose folder, write file, run `scripts/wiki-write`, append session log
   - If no, just log the session

## Chaining

**Into /study-flashcard:**
- After `/study-walkthrough` surfaces gaps → "Want to create flashcards for what we just covered?"
- After `/study-walkthrough` writes a wiki page → "Want to add key points as SRS flashcards?"
- After `/study` reveals weak areas → "Create targeted cards for struggling topics?"

**Out of /study-flashcard:**
- If developer can't explain a concept → chain to `/study-walkthrough` then return
- After creating cards → offer `/study` to immediately review them
- After creating cards + wiki page → offer `/study-walkthrough` for deeper exploration

## Guardrails

**Always:**
- Check `find_similar_cards` before creating ANY card
- Give the developer a chance to explain each concept before finalizing
- Use concrete code from the codebase, not abstract examples
- Default to fewer cards (2-3) not more

**Never:**
- Create cards without developer reviewing and approving each one
- Skip the duplicate check
- Create more than 5 cards in a single session without explicit request
- Add cards for concepts the developer already demonstrates mastery of

## Developer Preference — Card Style

The developer wants cards that support **high-level intuition and evaluation**, not detailed syntax recall. Favor cards about:
- Tradeoffs, design principles, "when/why to choose X over Y"
- Mental models, threat models, failure modes
- Concepts portable across languages/frameworks

Avoid cards about:
- Exact syntax, flag defaults, API method signatures, enum values
- Language/framework trivia that a reference doc or LSP would surface instantly

If a drafted card is pure syntax recall, flag it and ask whether there's a higher-level concept underneath worth capturing instead. When in doubt, ask — don't create the syntax card on assumption.

## Card Content Format — simple HTML, never markdown

Cards sync to AnkiWeb, and Anki note fields are **HTML**: markdown renders literally, raw newlines collapse, and unescaped `<`/`>` are parsed as markup. Author every `create_card`/`update_card` front and back in the simple HTML subset (it renders correctly on desktop, AnkiDroid, and AnkiWeb):

- Line breaks: `<br>` (never bare newlines)
- Inline code: `<code>...</code>`; code blocks: `<pre><code>...</code></pre>`
- Emphasis: `<b>`, `<i>` (never `**`/`*`)
- Lists: `<ul>/<ol>` with `<li>` (never `- ` / `1. ` lines)
- Literal angle brackets (e.g. a `<script>` XSS example) must be entity-escaped: `&lt;script&gt;` — typically inside `<code>`
- Never markdown links or `[[wikilinks]]` in card text — wiki linkage belongs in the companion page's `flashcard_ids`, not the card
- **Never a cloze deletion (`{{c1::…}}`).** Cards are question/answer style only: the front asks something, the back answers it. A cloze hands over the sentence frame, so it tests recognition of a missing word instead of a full retrieval attempt, and it makes it easy to smuggle two facts into one deletion. Rephrase the sentence into a question rather than blanking a span.
- **No em dashes (`—`), ever.** They're the classic LLM tell and read worse than plain prose. Write two sentences instead; after a bold lead-in label, use a colon (`<b>Fresh per response:</b> never reused…`). En dashes in numeric ranges (`1–4`) are fine.

When presenting a card draft in chat, show it rendered (readable), not as raw HTML. `scripts/card-htmlize` exists as a safety net that converts any markdown stragglers (dry-run by default, `--apply` to write), but new cards should be born clean.

These rules are **enforced at write time**: `create_card`/`update_card` reject markdown, bare newlines, wikilinks, and em dashes with a per-field error message. If a write is rejected, fix the draft per the error and retry — do not work around the validation.
