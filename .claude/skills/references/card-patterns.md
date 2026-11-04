# Card patterns

What a good software-engineering card and deck look like. Every skill that drafts or fixes cards reads
this. `card-quality.md` is what the gate holds a card to; this is how to write one that passes the first time.

## Before the card

- **Understand it first.** Cards are for remembering what was learned, not for learning it (Wozniak's rule 1,
  Sivers). No card from a tutorial or doc just skimmed: the walkthrough comes first.
- **Don't card what a lookup or an LSP answers at once**: flag defaults, signatures, enum values. Card what
  a lookup can't give you in the moment: how code behaves, why a design was chosen, what breaks.
- **A source's confident mistake gets memorized too.** Check a claim before it becomes a card
  (Nielsen: "if you commit such items to memory, you're actively making yourself stupider").

## The card

**Draft a claim, then its card.** A claim is a subject, one predicate and the moment it decides something. One claim, one card: a card written this way cannot be compound, where a card written directly merely tries not to be.

**Before writing a back, write the question's shortest correct answer. That is the back.** Then read the draft
twice: count what the front asks, then cover each sentence of the back and ask whether the answer still stands.

| Bad pattern | Bad | Good |
| --- | --- | --- |
| Two asks | What does CORS stand for and do? | What does a server's CORS header permit? |
| Rider without a question mark | Name the header that sets the preflight cache time, with its default. | Which header sets how long a preflight is cached? |
| Selection list | What are three ways session hijacking can occur? | An attacker on café Wi-Fi reads a session cookie off the wire. Which cookie attribute would have stopped that? |
| Fix tacked on | Why is <code>lock!</code> outside a transaction useless? ... Use <code>with_lock</code>. | Same front, back without the last sentence; a second card: which Rails method locks and opens the transaction for you? |
| Default tacked on | What does <code>Domain</code> do? It names the host. Omitted, it defaults to... | Same front, one claim; a second card: a cookie with no <code>Domain</code> is sent to which hosts? |
| Name tacked on | Who is blamed for a broken precondition? ... This is Meyer's Design by Contract. | Leave the name out, or give it its own card if the name is worth retrieving. |
| Example as a sentence | What is an origin? Scheme, host and port. <code>https://x.com:443</code> is one. | The back stops at "scheme, host and port". |
| Two independent reasons | Why is RAM not used for storage? It is volatile, and it is expensive. | One card per reason, each from the situation it decides. |
| Yes/no | Does the same-origin policy stop this transfer? No, because... | Why doesn't the same-origin policy stop this transfer? |
| Ambiguous | What is the private key used for? | In a TLS handshake, what does the server's private key prove? |
| No context | Which software principle supports passing the full object? | When a method takes a whole order rather than its id, which principle is being served? |
| Answer in the front | Which SOLID principle says modules depend on abstractions? | When a report's policy calls a mailer through an interface the policy owns, which principle is at work? |

Not flaws, so don't split them away:

- **A causal chain.** A "why" often needs two or three steps. Each is the answer.
- **A contrast.** "How does <code>preload</code> differ from <code>eager_load</code>?" needs both sides, and is one
  of the strongest kinds of card (the interference it trains is the point).
- **A closed set of up to three**, fixed by definition and recalled as one: Major, Minor, Patch. Longer ones,
  and ones someone merely selected, go one member at a time.
- **A few words of illustration inside a claim**: "a value unique to the operation, such as <code>order_id</code>".

## What to reach for, for code

Strongest first. All of these still ask one thing.

1. **Predict.** Surprising code, what does it evaluate to? (`var a = 5 + '5'` gives `'55'`.) Run it: a code card.
2. **Find the bug.** The listing is wrong and the output shows it. Reading code and seeing why it fails is what
   still pays with an assistant writing more of the code.
3. **A scenario with one decision.** A real situation, and the one thing it turns on.
4. **A gotcha pair.** Two near-identical cards whose difference is the lesson (`new Array('5')`, `new Array(5)`).
5. **A failure mode.** What breaks, under what load, and why.
6. **Definition.** The label alone, only for a term that keeps failing to come back.

## The deck

- **Many small cards beat a few big ones.** Coarser cards don't reduce what is to be learned (Matuschak). The
  reviews a small card costs are short, and a lapse repeats only the part that was forgotten.
- **Several angles on one idea are fine** when each is its own card and each is retrieved: redundancy isn't a
  breach of minimum information, which is about each repetition (Wozniak's rule 10). So is an integrative
  card once its parts are solid (Matuschak).
- **Near-duplicates are not angles.** Two cards with one answer and one question compete at recall.
  Fold them, or make them differ on purpose (a contrast).
- **Facts need practice as well.** A card and writing the code are different contexts. Code cards and real work
  close the gap; a deck alone doesn't.

## Fixing a back that says too much

The extra was usually worth knowing, which is how it got there. So it moves, it doesn't vanish:
- Shorten the back to the answer.
- Ask whether the extra is worth retrieving on its own. If yes, its own card, asked from a situation, not "what
  else is true of X". If not, or another card has it, it goes.
- Reduce before you split when what goes is filler: a restated question, a summary, a repeated idea.

## Sources

Wozniak, [Twenty rules of formulating knowledge](https://www.supermemo.com/en/archives1990-2015/articles/20rules);
Matuschak, [How to write good prompts](https://andymatuschak.org/prompts/);
Nielsen, [Augmenting long-term memory](https://augmentingcognition.com/ltm.html);
Sivers, [Memorizing a programming language](https://sive.rs/srs);
agentydragon, [My Anki patterns](https://www.lesswrong.com/posts/Mmk9tdFm8wcRvazva);
Chen, [Why LLM-generated flashcards are usually bad](https://dev.to/alexrchen/why-llm-generated-flashcards-are-usually-bad-and-how-to-screen-them-20mi),
on checking structure rather than asking a model to "be atomic".
