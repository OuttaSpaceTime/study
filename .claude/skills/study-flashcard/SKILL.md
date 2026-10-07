---
name: study-flashcard
description: "Create SRS flashcards directly: suggest a few ready card fronts on a topic, the developer picks or edits them, they are created. Checks pressure and existing cards first. For learning the topic itself, the developer calls /study-walkthrough or /study. Trigger keywords: create flashcard, add flashcard, new flashcard, make flashcard, cards on this."
user_invocable: true
---

# Flashcard Creator: suggest, pick, create

Turn a topic into 2-3 good cards in about two messages. Claude does the groundwork silently (pressure, existing cards, the wiki), then **suggests ready card fronts with their answers**. The developer picks, edits or rejects them in one reply, and the picked cards are created.

This is deliberately **not** a walkthrough. No checkpoints, no concept challenges, no "explain it back". When the developer wants to learn or probe the topic, they call `/study-walkthrough <topic>` or `/study` themselves. Offer that in one line when a topic looks unfamiliar; never start teaching here.

**Core guarantee:** every card that enters the deck was picked by the developer, passed the duplicate check, and meets the content rules below. Fewer, sharper cards beat more cards.

## Session Rules

See `~/.claude/skills/references/interactive-principles.md` for the shared principles.

- **Two beats:** the suggestion message, then the creation report. Add a third only when the developer edits or a check needs a decision.
- **Read silently, never cat.** `check_pressure`, `list_decks`, `find_similar_cards`, `mcp__qmd__query` and `Read` run without narration and without echoing their output. The chat shows the verdict line, the suggestions and the result. (AGENTS.md, "Read silently, never cat".)
- **Correct in place.** When the developer edits a suggestion, show the revised card once, replacing the old one. If a card is already created, fix it with `update_card`, never a second near-duplicate.
- Default to **2-3 suggestions**, at most 5. Suggest fewer when the topic is narrow.

## MCP Server Dependency

Requires `flashcard-mcp`. Tools: `check_pressure`, `list_decks`, `find_similar_cards`, `create_card`, `get_card`, `update_card`. Use `find_similar_cards` for duplicate checks: it is semantic. `search_cards` is substring only.

## Invocation

```
/study-flashcard                          ask for the topic in one line
/study-flashcard <topic>                  cards on a topic
/study-flashcard <topic> <deck-name>      cards on a topic, in that deck
/study-flashcard --from <url>             cards from a page (WebFetch it)
/study-flashcard <a paragraph of text>    cards from the text's key ideas
```

The Omvida app (`~/Code/omvida`, Add → Flashcards) opens this skill as `/study-flashcard <topic>` with a `Context:` line under it:

- `Context: wiki page [[folder/slug]]`: read that page silently and suggest cards for what it teaches that its `flashcard_ids` do not cover yet.
- `Context: flashcard <id>: <front>`: the developer was studying that card. Suggest cards for the neighbouring ideas or the gap it exposed, not a rephrasing of it.

## Step 1: Pressure preflight (always first)

Call `check_pressure` before anything else and follow `references/srs-pressure-check.md`.

- `ok`: one line, `SRS pressure: ok.`, and continue to the suggestions in the same message.
- `warn`: the counts, the reasons and the clearance in one or two lines, then the reference's gate question, and wait. The guard is one the developer asked for; being direct does not mean skipping it. On "continue", suggest at most 2 cards.
- `pause`: the server refuses fresh cards. Say so with the clearance numbers and stop. Splits (`inheritFrom`) and `update_card` still work, so a fix to an existing card is fine.

## Step 2: Groundwork (silent)

1. **Deck.** `list_decks`. Pick the deck that already holds this topic's cards. Ask in one line only if two decks fit equally.
2. **What exists.** `find_similar_cards` with the topic, and with each draft front before suggesting it. Read `wiki/.wiki-index.json` for a page on the topic and its `flashcard_ids`.
3. **Draft and filter.** Draft more fronts than you will show, then drop any that fail the quality checks below or sit above 80% similarity to an existing card. Only suggestions that already pass are shown.

## Step 3: Suggest (one message)

Lead with one line on existing coverage when there is any ("You have 4 cards on CSP; these cover what they don't."). Then the numbered suggestions, each with its front as the title and the answer under it, rendered (not raw HTML):

> **1. Two URLs differ only in port. Same-origin policy: blocked or allowed, and why?**
> Blocked. The origin is scheme, host and port, so a different port is a different origin.
> *guided · #security #web*
>
> **2. …**
>
> Pick (`1,3`), edit (`2: shorter answer`), `all`, or `none`.

- A suggestion in the **50-80% similarity band** carries one extra line naming the close card: *close to "What does the Expires attribute do?"; say how the answers differ, or skip it.* That band is an interference risk: sibling cards that differ only in which attribute they name compete at recall. If the developer cannot separate them, fold the two into one contrasting card instead of creating both.
- If the topic looks new to the developer, end with one line: *To learn it first: `/study-walkthrough <topic>`.*

## Step 4: Create and report

1. `create_card` for each picked card, with deckId, front, back, tags and type.
   - **Derived from an existing card** (a split or rephrasing of one with review history)? Pass `inheritFrom: <original id>` on every `create_card`, then delete the original. The new cards keep its FSRS schedule instead of arriving as new cards.
2. Report in one or two lines: how many were created, and each card's front in short.
3. **Push to AnkiWeb:** run `scripts/anki-sync sync` silently. Mention it only if it moved something or failed (one line, never blocking).
4. **Link the wiki:** if a wiki page covers the topic, add the new ids to its `flashcard_ids` and run `scripts/wiki-write <page>` (the wiki-write protocol's index and lint step). Say it in one line. If no page exists, offer once: *No wiki page yet; `/study-walkthrough --write <topic>` writes one.*
5. Append the session log entry (`## Session N — Flashcard (HH:MM)`: topic, cards created, deck, wiki page linked) to `logs/<MM>/<YYYY-MM-DD>.md`.

## Guardrails

**Always:**
- Run the pressure preflight first, and `find_similar_cards` on every front before suggesting it.
- Let the developer pick. Nothing is created that was not picked.
- Prefer 2-3 cards. More only on explicit request, and never more than 5 in one go.

**Never:**
- Turn this into a walkthrough: no teaching sequence, no comprehension checks, no "explain it back". Point at `/study-walkthrough` instead.
- Create a card the duplicate check flags above 80% without the developer saying so explicitly.
- Suggest a card that fails the checks below, hoping the developer will fix it.

## Quality checks on every suggestion

These mirror `/study`'s review-time flags and the Omvida grader's card check. Catching them here costs one draft; catching them in review costs months.

- **One recall target.** No superlatives or judgments with several defensible answers ("the single most effective", "the best way"). Name the scenario or principle being tested instead.
- **Self-contained front.** Exactly one answer is right without seeing the back. "What is the private key used for?" could mean TLS, JWT or SSH. Write "In a TLS handshake, what does the server's private key do?". This *Ambiguous front* is the most common defect in the deck.
- **A back worth learning.** A precise one-liner is fine; a vague gesture ("store sensitive data in the database") is not.

## Developer preference: judgment over definitions

The developer wants cards that build **intuition and evaluation**: tradeoffs, when and why to choose X over Y, mental models, threat models, failure modes, concepts that travel across languages. Not exact syntax, flag defaults, method signatures or enum values a reference or LSP surfaces instantly.

### The definition trap

A September 2026 audit found 70% of the deck asking what something *is* and only 2% asking for a flag value. A definition card teaches the label, not a decision. **Suggest the judgment version first**, and the definition only when the term itself is what keeps failing to come back.

| Definition (weaker) | Judgment (stronger) |
| --- | --- |
| What is session fixation? | What does an attacker gain by fixing the session ID *before* login that they couldn't get after? |
| What is an "origin" in web security? | Two URLs differ only in port. Same-origin policy: blocked or allowed, and why? |
| What is the Composite pattern? | What does Composite buy you that a plain list of children doesn't? |

The strongest cards pair a **concrete front** (a real scenario to reason over) with a **transferable answer** (a principle that travels). Only 13% of the deck does both; that is the headroom.

## Card Size & Scope: one question, short answer

Enforced at write time by `create_card`/`update_card`. A violating card is rejected.

| Rule | Limit | Measured on |
| --- | --- | --- |
| Answer length | **200 characters** | Visible text: markup and entities are not counted |
| Answer shape | **4 sentences** | Terminal punctuation, plus each `<li>` and `<br>` |
| Front | **one question** | Heuristic: 2+ question marks, or `and`/`or` + a question word |

Markup is free, so `<code>`, `<b>` and `<ul>` never cost budget. Fronts have **no** length limit: a grounded scenario front is good.

**Write the answer like this:** the answer first, then at most one clause of why. No throat-clearing, no restated question, no summary sentence.

Too long (300 chars), the last clause is filler:

> Access and manipulate sensitive data, make authenticated requests, and interact with the DOM. For example, a malicious script running on evil.com could extract banking details from your authenticated bank.com session, effectively seeing everything you can see and stealing your sensitive information.

On point (161 chars):

> It acts as the user. It can read the DOM, make authenticated requests, and exfiltrate data from the target origin. Anything the user can see or do, the script can.

### When a write is rejected

The error names the field and both remedies. In this order:

1. **Reduce.** Cut filler, the restated question, the trailing summary. Most rejections are padding. This is the developer's stated preference.
2. **Drop the extra question.** Keep the one the card is really about.
3. **Split**, only when the dropped idea has no other card (check with `find_similar_cards`). A split off a reviewed parent passes `inheritFrom`.

Never rephrase just to slip past the check. The one-question check is a regex and can misfire: if it rejects a front that asks **one** question, show the developer the flagged phrase and let them decide. It already allows conjunctions that join subjects ("how do Bundler <b>and</b> Yarn resolve…").

## Card Content Format: simple HTML, never markdown

Cards sync to AnkiWeb, and Anki fields are **HTML**: markdown renders literally, newlines collapse, and bare `<`/`>` parse as markup. Write every front and back in this subset:

- Line breaks: `<br>`, never bare newlines
- Inline code `<code>…</code>`; code blocks `<pre><code>…</code></pre>`
- Emphasis `<b>`, `<i>`, never `**` or `*`
- Lists `<ul>`/`<ol>` with `<li>`, never `- ` or `1. ` lines
- Literal angle brackets entity-escaped: `&lt;script&gt;`, typically inside `<code>`
- No markdown links and no `[[wikilinks]]`: wiki linkage lives in the page's `flashcard_ids`
- **No cloze deletions (`{{c1::…}}`).** Question and answer only. A cloze hands over the sentence frame and tests recognition, not retrieval.
- **No em dashes (`—`, `&mdash;`, `&#8212;`, `&#x2014;`), ever.** Write two sentences, or use a colon after a bold label. En dashes in ranges (`1–4`) are fine.

Show drafts rendered in chat, never as raw HTML. These rules are enforced by `create_card`/`update_card` with a per-field error; fix the draft per the error and retry. `scripts/card-htmlize` converts markdown stragglers, but new cards should be born clean.

## Chaining

- **Into this skill:** Omvida's Add → Flashcards and a wiki page's "Cards on this page"; `/study-walkthrough` after it writes a page ("Add the key points as cards?"); `/study` when a session exposes a gap.
- **Out of it:** `/study-walkthrough <topic>` to learn first or go deeper; `/study` to review the new cards. Offer each in one line at most, never both at once.
