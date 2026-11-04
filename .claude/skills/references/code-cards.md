# Code cards

A code card is answered by running it. Omvida runs the code in a sandbox and compares values, after
Execute Program, which the developer has used and rates highly. This page is how to choose, write and
check one. Every skill that writes or fixes cards reads it first; `card-quality.md` is what the gate
then holds the card to.

## When to write one

Write a code card when what is being learned is **how code behaves**, and running it can tell a right
answer from a wrong one. Keep a plain card for what doesn't run: tradeoffs, why a design was chosen,
threat models. Execute Program's conceptual lessons fit its format badly, for the same reason.

With an assistant writing more of the code, what still pays is **reading code and seeing why it fails**.
In Anthropic's 2026 trial, debugging was where learning with AI fell furthest behind. So:

| Prefer | Over |
| --- | --- |
| Predict what surprising code evaluates to | Recall a method name |
| Find the bug: the listing is wrong, the output shows it, fix the blank | Fill in syntax |
| A contrast (`each` beside `map`, `==` beside `equal?`) | One API in isolation |
| The concept, breadth first | Version quirks, exact signatures |

## The three kinds

| Kind | The developer | The format | On Anki |
| --- | --- | --- | --- |
| `predict` | reads the code, types what each `expr` evaluates to | no blanks; each case's `goal` is hidden | cloze |
| `fill` | completes `{{c1::blanks}}` until every `expr` equals its `goal` | goals in plain sight | cloze |
| `compose` | the same with bigger pieces: a whole method body, several small parts together | a multi-line blank is a block to write | front and back |

```json
{
  "kind": "fill",
  "lang": "ruby",
  "brief": "Keep the even numbers, squared.",
  "source": "def even_squares(list)\n  list.select(&:even?).{{c1::map}} { |n| n * n }\nend",
  "cases": [
    { "expr": "even_squares([1, 2])", "goal": "[4]" },
    { "expr": "even_squares([3])", "goal": "[]" }
  ],
  "explain": "<code>select</code> narrows, <code>map</code> transforms."
}
```

- **`brief`**: what to solve, one or two sentences of simple HTML, without the answer.
- **`source`**: as little code as the idea needs. It is one screen at most.
- **`cases`**: `goal` is an expression (`[1, 2]`, `nil`, `"yes"`), compared with `==` to what `expr`
  gives. Several cases are several inputs, and a good second case catches the tempting wrong answer.
- **`explain`**: the why, shown once it is over. It is feedback, not an answer to recall, so naming the tempting wrong answer is fine and the gate doesn't count it as extra. It can still be wrong, or give the card away. A card's back limits apply.
- **Blanks**: always `c1`. Every blank is hidden and answered together, as one review.
- Only Ruby has a runner so far. It runs the newest Ruby mise has, which can differ between machines.

## Checking one: run it, don't trust it

1. **`check_code_card`** while drafting. It saves nothing. It runs the solution and returns what each
   case really gives, the `problems` that would refuse it, and the `sides` it would have. Read the real
   values before showing a draft: a surprise here is usually the card's best idea, or a mistake.
2. **`create_code_card`** or **`update_code_card`** makes the same checks and refuses on any problem:
   the solution doesn't pass, it passes with every blank `nil`, or two runs differ. The card-quality
   gate then judges what a run can't: whether it is a good question.

A goal is never hand-written and left unchecked. `get_card` returns a code card's `exercise`, its
solutions included.

Show a draft to the developer as the code with its blanks and goals, rendered, and say what kind it is.
Don't show raw JSON.

## How it is reviewed

Execute Program's rules, which the deck server holds:

- A real interpreter evaluates the answer, so any equivalent answer passes (`%w[a b]` for `["a", "b"]`).
- **Tries are unlimited, and wrong ones and errors cost nothing.** A pass is Good however many it took.
- **Giving up is the one failure**: it shows the solution and rates Again.
- The developer doesn't rate it. The result does.
- A `predict` card shows nothing of the real value until it passes. The others show their output as
  the developer types, with errors as Ruby prints them.

On the phone there is no runner, so a code card is an ordinary cloze or front-and-back card, rated by
hand. The schedule is shared. It stays FSRS: Execute Program's own review levels aren't copied.

In a `/study` chat, check an answer with `run_code_card` (one answer per blank, or per case on
`predict`), and `reveal_code_card` once the developer gives up. Neither writes anything: pass the
`rating` they return to `submit_review`.

## Changing one

- A fix goes through `update_code_card`, which takes the whole exercise. `update_card` can change only
  tags and category.
- A split is `create_code_card` for each part with `inheritFrom`, then `delete_card` on the original.
- **A card keeps its kind for life**: plain or code, and within code `compose` stays `compose`.
  An Anki note can't follow a change without a full upload. To change kind, create a new card with
  `inheritFrom` and delete the old one.
- **Clozes exist only on code cards.** `create_card` and `update_card` refuse `{{c1::...}}` anywhere in a
  front or back, inside `<pre>` too: a plain cloze hands over the sentence frame, and tests recognition
  rather than retrieval. Don't write one by hand here either: the blanks in `source` are the format, and
  flashcard-mcp writes the cloze from them.
