---
name: study-card-check
description: "Check one flashcard's quality and fix it unattended: judge it against references/card-quality.md and, when it has a real flaw, correct, rewrite or split it (inheritFrom), never losing information. Runs headless from Omvida's Ctrl+Q (`claude -p \"/study-card-check <card id>\"`) and ends with one line saying what it did. Trigger keywords: check card quality, card check, fix this card's quality."
user_invocable: true
---

# Card check

The developer pressed Ctrl+Q on a card in Omvida's study loop: "this card looks off, deal with it".
This runs **headless and unattended** (`claude -p`): nobody reads the conversation, nobody answers
a question. Decide, act, and end with one line the app shows as a toast.

The card-quality gate (`scripts/card-quality-gate`) judges every `create_card` and `update_card`
here too, so a fix that is itself flawed is refused with the reason.

## Rules

- **Judge against `.claude/skills/references/card-quality.md`** (read it first). Only real flaws:
  a card that is fine stays exactly as it is. Changing a sound card is the worst outcome here.
- **Keep the information.** Follow the reference's "Fixing a flaw" order: correct, rewrite, or
  split. Never drop an idea no other card holds; check with `find_similar_cards`.
- **A split** is `create_card` for each part with `inheritFrom: "<card id>"`, the original's deck
  (`deckId` from `get_card`), tags and type, then `delete_card` on the original, only after every
  part was created. Splits keep the schedule and are exempt from the pressure limits.
- **Check a fact before calling the back wrong**: `mcp__qmd__query` on the wiki, then the web
  (WebSearch, WebFetch on the most authoritative result).
- **Format and size** are `/study-flashcard`'s (read its "Card Size & Scope" and "Card Content
  Format" before writing).
- **Never** rate, start or end a session, touch card notes, or edit any other card than this one
  and its split parts.
- **A refused write**: revise per the gate's reason and try again, at most twice. Still refused:
  leave the card as it is and say so. A split refused part-way is undone: `delete_card` every part
  this run created, so the original stays the only card. Nobody can be asked: where the gate's
  reason says to show the developer, this run gives up instead.

## Steps

1. `get_card` with the id given. Missing: say so and stop.
2. Read the reference, judge the card.
3. Sound: change nothing.
4. Flawed: fix it as above.
5. The last message is **one line**, nothing else, starting with what happened:
   - `No change: <why it is sound, a few words>.`
   - `Fixed (<issue>): <what changed, a few words>.`
   - `Split (<issue>) into <n> cards: <their fronts, short>.`
   - `Unchanged: <why the fix could not be saved>.`
