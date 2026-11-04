# Card quality

What makes a flashcard flawed, in one place: the card-quality gate
(`scripts/card-quality-gate`, a hook on every `create_card`, `update_card`, `create_code_card` and
`update_code_card`) judges each card
written against it, and `/study-card-check` judges (through the same judge) and fixes one card against it. `/study-flashcard`'s
"Quality checks" are the same list, seen from the drafting side; `card-patterns.md` has the good and
bad patterns to draft from.

Why a card has one job, whatever else it does: a card gets one rating. A card that asks two things tells
the scheduler both are known when only one was, and the weaker one is never repeated at its own pace.
A fact the front did not ask for costs attention at every review and is read, not retrieved, so it
is not being learned. This is Wozniak's minimum information principle and Matuschak's "focused"; a
fact worth keeping belongs on a card of its own, where it is retrieved.

## Count first: one thing asked, one thing answered

**Count what is asked.** List each thing the developer must retrieve, one entry each:

- A second question counts, and so does a rider with no question mark ("with an example", "and its
  default", "and name the axis", "and do").
- A list counts per member, one entry per member, when it is a selection someone chose: "three ways",
  "key characteristics", "common examples", "name 3+", "what are the properties of". So do attributes
  that each carry a fact of their own. List them all: never one entry for the whole list.
- The back decides as well: a "why" whose back gives two independent reasons, either of which would be a
  full answer, asks two things. "What does X do" whose back gives two unrelated effects, the same.
- One entry: a closed set fixed by definition with at most three members, recalled as one whole (the
  parts of a SemVer version, of an origin); scenario setup in the front; a single contrast or comparison,
  both of whose sides the front needs ("A vs B", "when A over B", "how does A differ from B").

**Count what the back says.** List its claims, and mark each:

- `answer`: it answers something asked.
- `step`: a step of the causal chain a "why" or "how" needs, or the other side of a contrast.
- `extra`: remove it and the answer is still correct and complete, and it states a fact of its own:
  a fix or advice the front did not ask for ("Use X", "Prefer Y", "Better: Z"), a consequence, a default,
  a requirement, a tool, a name, a date, a history, a full-sentence example, an alternative, a restatement.

A few words inside a claim that only illustrate it ("such as <code>order_id</code>") or say what it is
for are part of that claim, not a claim. Split claims by fact, not by comma.

**The card fails with more than one entry asked (`not_atomic`), or with any `extra` (`extra_info`).**

| Card | Count | Verdict |
| --- | --- | --- |
| "What does CORS stand for and do?" | asked: its expansion, what it does | fails |
| "Which three headers harden a session cookie?" | asked: Secure, HttpOnly, SameSite | fails |
| "What does <code>Secure</code> do?" / "Sends the cookie over HTTPS only. Set it on every session cookie." | answer, extra | fails |
| "Why does the row stay locked?" / "The lock lives until commit, and the transaction is still open." | step, step | passes |
| "When do you pick a nonce over a hash?" / "Nonce for server-rendered scripts; hash for static ones." | answer, step | passes |

On a code card, `asked` counts ideas, not cases or blanks: several cases exercising one idea are one
entry. `explain` is feedback shown once the card is passed, not an answer to recall, so it is never counted as
extra, and naming the tempting wrong answer is its job: mark its claims `step`. It can still be `incorrect`, or
give the card away.

## The other flaws

A card is not flawed for being short when its back is precise, for asking for a definition (the deck
prefers judgement cards, but that is a drafting preference, not a flaw), or for wording you would have
chosen differently: only clear flaws here, and a simplification is not `incorrect`. A code card is fine for
having `{{c1::...}}` blanks, the only cards allowed them, and its goals flashcard-mcp has already run. A
cloze on any other card is refused before it gets here. Format
and size (HTML, the back's size, one question mark) are enforced by flashcard-mcp itself and are
not judged here.

| Issue | The card is flawed when |
| --- | --- |
| `incorrect` | The back is factually wrong, or wrong in part: it would teach something false. The worst flaw there is. |
| `too_vague` | The back is too thin to learn from: a gesture ("a security feature"), not an answer. |
| `ambiguous_front` | The front has more than one right answer without seeing the back ("what is the private key used for?": TLS, JWT or SSH?), or leans on context it does not give ("why is that a problem?"). |
| `opinion_bait` | The front asks for a "best" or "single most" with no single defensible answer. |
| `yes_no` | The front can be answered "yes" or "no", so a coin flip passes it, and what it means to teach is in a back the front never asked for. Ask for that directly: "Why doesn't...", "What stops...". |
| `gives_away` | The front contains the answer, or most of its words. |
| `mismatched` | The back answers a different question than the front asks: asks what, answers why, or the reverse. |
| `outdated` | The back teaches a deprecated API, pattern or practice as current (MD5 for passwords, XMLHttpRequest as the way to fetch). |

### On a code card

A code card comes to the judge as its exercise: its kind, what to solve, the code with each solution
in `{{c1::...}}`, and each case's expression and goal (`.claude/skills/references/code-cards.md`). A `predict` card's
goals come in `{{c1::...}}` as well, being hidden from the developer until they answer.
flashcard-mcp has already run it, so its goals are true: `incorrect` is about what its `explain`
says. The count above and the flaws above apply too (`not_atomic`, for a card that needs two ideas), and these:

| Issue | The card is flawed when |
| --- | --- |
| `gives_away` | On a code card too: the brief, a comment or a visible goal hands over the answer, so nothing is left to work out. Goals in plain sight are normal on `fill` and `compose`: flawed only if one reads off as the blank itself. |
| `tests_spelling` | A blank asks only for a name or syntax an LSP would offer, with no behaviour to reason about: nothing in the code or the goals tells a right answer from a wrong one except having memorised it. |
| `padded_code` | Code beyond what the idea needs: setup to scroll past, or more than a screen. |
| `fragile` | The value depends on the Ruby version, the machine, the time or randomness, in a way two runs on one machine wouldn't show. |

## Fixing a flaw: keep the information

A fix must not lose what the card knew. In order of preference:

- `incorrect`, `outdated`: correct the back (`update_card`). Check the fact first (the wiki through
  `mcp__qmd__query`, or the web) rather than trusting a hunch.
- `too_vague`: give the back its missing substance, within the size rules.
- `ambiguous_front`, `opinion_bait`, `mismatched`, `yes_no`, `gives_away`: rewrite the front (or the back) so the
  card asks and answers one thing.
- `tests_spelling`, `padded_code`, `fragile`, and `gives_away` on a code card: rewrite the exercise (`update_code_card`),
  aiming at the behaviour behind it: a `predict` card or a find-the-bug often says it better. Try it with
  `check_code_card` first. A change of kind is a new card with `inheritFrom` (code-cards.md, "Changing one").
- `extra_info`: the back loses the extra. Each extra fact goes on a card of its own, where it is
  retrieved, unless another card already holds it (`find_similar_cards` above 80%), or it was only a restatement.
  Asking it of a real situation beats a bare "what is".
- `not_atomic`: **split**, one card per thing asked. A selection list becomes one card per member,
  each with a front that singles it out: not "name the three", but the situation only that member answers.

A split is a `create_card` per part with `inheritFrom: "<the card's id>"` (it keeps the original's
schedule, and splits are exempt from the pressure limits), same deck, tags and type; then `delete_card`
the original, and only once every part exists. When only an extra moves out, the original stays: its
`update_card` is the shorter back, and the extra's card has `inheritFrom` too.

The card content format and size rules are `/study-flashcard`'s ("Card Size & Scope", "Card
Content Format").
