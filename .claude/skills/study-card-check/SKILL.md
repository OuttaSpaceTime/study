---
name: study-card-check
description: "Check one flashcard's quality and fix it unattended: count what it asks and what its back says, judge it against references/card-quality.md and, when it has a real flaw, correct, rewrite or split it (inheritFrom), never losing information. Runs headless from Omvida's Ctrl+Q (`claude -p \"/study-card-check <card id>\"`) and reports what it counted and did. Trigger keywords: check card quality, card check, fix this card's quality."
user_invocable: true
---

# Card check

The developer pressed Ctrl+Q on a card in Omvida's study loop: "this card looks off, deal with it".
This runs **headless and unattended** (`claude -p`): nobody reads the conversation, nobody answers
a question. Decide, act, and report what you counted and did: the app lays it out in a slot beneath the card,
where the developer can read it, dismiss it or discuss it.

The card-quality gate (`scripts/card-quality-gate`) judges every `create_card`, `update_card`,
`create_code_card` and `update_code_card` here too, so a fix that is itself flawed is refused with the reason.

## Rules

- **The verdict is the gate's, not yours.** Run `scripts/card-quality-gate --judge <card id>`: the same judge
  that holds every write, so the check and the gate cannot disagree. It prints `passes`, `asked` (each thing the
  card asks), `claims` (each thing its back says, `answer`, `step` or `extra`), `issues` and `parts` (the fronts of
  cards already made from this one). A card that passes
  stays exactly as it is, however you might have worded it. Changing a sound card is the worst outcome here.
  Read `.claude/skills/references/card-quality.md` for what the issues mean and how each is fixed, and
  `.claude/skills/references/card-patterns.md` to write the fix.
- **Keep the information.** Follow the reference's "Fixing a flaw" order: correct, rewrite, or
  split. Never drop an idea no other card holds; check with `find_similar_cards`. An `extra` claim that holds a
  fact worth keeping moves to a card of its own (`create_card` with `inheritFrom`) when the back is shortened.
- **A split** is as the reference says, with the original's `deckId` from `get_card`. If the judge's `parts`
  names cards already, a run cut short made those from this one: don't make them again, make the rest.
- **Check a fact before correcting a back for `incorrect`**, the judge's word alone is not enough: `mcp__qmd__query` on the wiki, then the web
  (WebSearch, WebFetch on the most authoritative result).
- **A code card** (`get_card` returns its `exercise`) is judged on the reference's "On a code card" as
  well, and on `.claude/skills/references/code-cards.md`, which read first. Run it with `check_code_card`,
  rather than judging its behaviour from reading it. A fix is `update_code_card`, tried with
  `check_code_card` first; a split or a change of kind is `create_code_card` with `inheritFrom`, then
  `delete_card`. A sound code card that merely could have been a different kind stays as it is.
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
2. `scripts/card-quality-gate --judge <id>`.
3. Passes: change nothing.
4. Fails: read the references, fix it as above. After any split or moved extra, `scripts/card-links-sync`, so wiki
   pages that listed this card list its parts.
5. The report:
   - `outcome`: `no_change` (it passes), `fixed` (the card was rewritten, an extra perhaps moved out),
     `split` (the original is gone, its parts hold everything), or `unchanged` (it is flawed, and no fix would save).
   - `summary`: one or two plain sentences saying what was wrong and what you did, or why it is sound.
   - `asked`: the judge's `asked`. `extra`: the text of its claims marked `extra`.
   - `cards`: every card as it now stands that this run wrote, its `front` and `back`. Empty if none was written.
