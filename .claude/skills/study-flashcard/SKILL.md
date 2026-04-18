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

**At any point** during the session, the developer can say "show in Obsidian" to launch Obsidian and view wiki pages. Follow the "Show in Obsidian" flow in the wiki-write-protocol.

## Session Rules

For additional shared interactive principles (scope, handling disagreement, non-interactive mode), see `~/.claude/skills/references/interactive-principles.md`.

- ONE concept per message, under 150-200 words of prose. Pause for discussion.
- If the developer already knows the topic well, compress Checkpoint 2 and move to drafting.
- Start each checkpoint with `Checkpoint X/4: <title>`.
- Pause after each checkpoint — ask whether to continue or discuss. Never auto-advance.
- At each checkpoint, blend guided and unguided modes.

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

## Checkpoint Flow

### Checkpoint 1/4: Topic & Scope

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
2. **Semantic duplicate check**: Call `find_similar_cards` with the draft front text
   - >80% match: "Very similar card exists. Skip or rephrase?"
   - 50-80% match: "Related card exists. Your new card covers a different angle — proceed?"
   - No matches: "No similar cards found. This is new territory."
3. Ask the developer to explain the concept in their own words
4. Developer says "good", "next", "edit", or "skip" for each draft

### Checkpoint 4/4: Confirm, Create & Write Wiki

1. Present all approved drafts in a numbered list
2. Developer confirms: "Create these" or makes final edits
3. For each approved draft, call `create_card` with deckId, front, back, tags, type
4. Report results
5. **Offer "write wiki"**: "Want to save a companion wiki page for these concepts?"
   - If yes, follow the full flow from `references/wiki-write-protocol.md`:
     - Draft a wiki page that goes beyond a thin summary — include context, examples, and the developer's own explanations from the walkthrough
     - Include `flashcard_ids` in frontmatter with the IDs of created cards
     - **Required:** link to at least 2 related wiki pages via `[[absolute/path]]` — search the index for connections. Companion pages must not be leaf nodes in the graph.
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
