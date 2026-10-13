---
name: study-fix-notes
description: "Work through the card notes the developer left while studying (Omvida's Ctrl+N): for each noted flashcard, read the note and do what it asks, a fix to the card drafted and written, or a question about it worked through Socratically, then resolve the note. Trigger keywords: fix notes, noted cards, card notes, fix noted cards, handle my notes."
user_invocable: true
---

# Fix noted cards

While studying in the Omvida app (`~/Code/omvida`) the developer notes a card instead of stopping to fix it (Ctrl+N): what should change about it, or what they want to understand better, in their own markdown. The notes live in the deck (flashcard-mcp's `CardNote`, one per card) until this skill handles them. Noting is for dealing with them together, later: this is that session.

**Core guarantee:** no card is written without the developer seeing the draft, and no note is resolved until the developer agrees it is dealt with. A note skipped stays open for next time.

## Session Rules

- **One note at a time, oldest first.** Finish or skip one before showing the next.
- **Read silently, never cat.** `list_card_notes`, `find_similar_cards`, `mcp__qmd__query` and `Read` run without narration (AGENTS.md, "Read silently, never cat").
- **Never rate.** Don't call `submit_review`, `start_session` or `end_session`: Omvida records the developer's ratings, and this is not a study session.

## MCP Server Dependency

Requires `flashcard-mcp`. Tools: `list_card_notes`, `resolve_card_note`, `get_card`, `update_card`, `create_card`, `delete_card`, `find_similar_cards`.

## Invocation

```
/study-fix-notes                   every open note
/study-fix-notes <card id> ...     the notes on those cards only
```

Omvida opens it with the card ids of the notes it means: a finished session's noted cards (its summary), or the cards its Cards screen's "noted" filter leaves. "Fix all" on Omvida's Home opens it with none.

## Step 1: The notes (silent)

Call `list_card_notes`: every open note, oldest first, each with its card (id, deck, front, back, tags, lapses). With card ids given, keep the notes on those cards, in that order. If none are left, say so in one line and stop: a note may have been resolved since the app listed it.

Open with one line: how many notes, and the cards' fronts in a few words each.

## Step 2: Each note

Show the card (its front and back rendered, not raw HTML) and the note verbatim. Then decide what the note asks for, and say which in a few words:

- **A change to the card** (reword, tighten, split, fix a wrong back, retag): draft the fix following `/study-flashcard`'s card content format and size rules (read its skill file for them). Show the draft, and write it once the developer agrees: `update_card` for an edit; for a split, `create_card` for each part with `inheritFrom: "<the card's id>"` so the parts keep its schedule, then `delete_card` the original. Run `find_similar_cards` on a new front first, as `/study-flashcard` does.
- **Something to understand better** (a "why", a confusion, a link to another idea): use `/study`'s Socratic mode, as its section "Fast Feedback by Default, Socratic on Request" describes: decompose into smaller questions, never hand over the answer. If a gap shows, offer a card for it (`/study-flashcard`'s rules) or `/study-walkthrough <topic>` in one line.
- **Anything else** the note asks: do it, within the study repo's rules (AGENTS.md).
- **Unclear:** ask what the note meant in one line.

A note can ask for both: understand first, then fix the card if the understanding changes it.

## Step 3: Resolve

Once the developer agrees a note is dealt with, call `resolve_card_note` with its card id; Omvida drops it from its lists. When they skip a note, leave it open and go on. A card split or deleted takes its note with it, so there is nothing to resolve then.

## Step 4: The end

One line: how many notes were resolved, and which were left open.
