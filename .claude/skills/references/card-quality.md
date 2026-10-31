# Card quality

What makes a flashcard flawed, in one place: the card-quality gate
(`scripts/card-quality-gate`, a hook on every `create_card` and `update_card`) judges each card
written against it, and `/study-card-check` judges and fixes one card against it. `/study-flashcard`'s
"Quality checks" are the same list, seen from the drafting side.

Only real flaws count. A card is not flawed for being short when its back is precise, for asking
for a definition (the deck prefers judgement cards, but that is a drafting preference, not a flaw),
or for wording you would have chosen differently. When in doubt, it passes. Format and size
(HTML, the 200-character back, one question mark) are enforced by flashcard-mcp itself and are not
judged here.

## The flaws

| Issue | The card is flawed when |
| --- | --- |
| `incorrect` | The back is factually wrong, or wrong in part: it would teach something false. The worst flaw there is. |
| `too_vague` | The back is too thin to learn from: a gesture ("a security feature"), not an answer. |
| `too_broad` | The front covers several concepts ("explain session security"), so no single answer is the right one. |
| `two_questions` | The front asks two things ("what is X, and how do you prevent it?"). |
| `ambiguous_front` | The front has more than one right answer without seeing the back ("what is the private key used for?": TLS, JWT or SSH?), or leans on context it does not give ("why is that a problem?"). |
| `opinion_bait` | The front asks for a "best" or "single most" with no single defensible answer. |
| `mismatched` | The back answers a different question than the front asks: asks what, answers why, or the reverse. |
| `verbose_answer` | The back pads: it restates the question, or adds a second idea the front does not ask for. |
| `outdated` | The back teaches a deprecated API, pattern or practice as current (MD5 for passwords, XMLHttpRequest as the way to fetch). |
| `cloze` | The card is a cloze deletion (`{{c1::...}}`). |

## Fixing a flaw: keep the information

A fix must not lose what the card knew. In order of preference:

- `incorrect`, `outdated`: correct the back (`update_card`). Check the fact first (the wiki through
  `mcp__qmd__query`, or the web) rather than trusting a hunch.
- `too_vague`: give the back its missing substance, within the size rules.
- `ambiguous_front`, `opinion_bait`, `mismatched`: rewrite the front (or the back) so the card asks
  and answers one thing.
- `two_questions`, `too_broad`, `verbose_answer`: **split**, one card per idea. Each part is a
  `create_card` with `inheritFrom: "<the card's id>"` (it keeps the original's schedule, and
  splits are exempt from the pressure limits), same deck, tags and type; then `delete_card` the
  original, and only once every part exists. An idea may be left out only when another card
  already holds it (`find_similar_cards` above 80%).
- `cloze`: rewrite as a question and answer.

The card content format and size rules are `/study-flashcard`'s ("Card Size & Scope", "Card
Content Format").
