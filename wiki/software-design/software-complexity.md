---
title: Software complexity
aliases:
- accidental complexity
- essential complexity
- complexity cost
- why lower complexity
tags:
- software-design
- complexity
- code-review
created: '2026-07-03'
updated: '2026-07-03'
source_skill: study-walkthrough
flashcard_ids:
- cmruqtu290004qo0meh4jat6l
- cmruqtwrm0005qo0m1zn2mdei
review_interval: 4
next_review: '2026-07-25'
---

# Software complexity

Complexity is not file length or `if` count. It is the gap between what a change should cost and what it actually costs, and most of that gap stays invisible until you try to change the code, not while you are reading it. This page gives the vocabulary for naming where complexity comes from, why it hides from a read, and when it is actually worth the cost of removing.

## TL;DR

- **Essential complexity** comes from the real constraints of the problem. **Accidental complexity** comes from how the code happens to be written, and buys nothing the essential version does not already buy.
- Reading tolerates a partial understanding. Modifying safely does not, so complexity's pain shows up at change time, not read time. A check's shape gives no visual signal either way, that is obscurity.
- **Complecting** braids two independently simple things together. Neither half looks complex alone, the cost shows up only once you need to change one without the other.
- A guarantee should be established once, at the boundary where untrusted input enters, and relied on everywhere inside that boundary. Re-checking it downstream is accidental complexity with no offsetting benefit.
- AI-generated code produces plausible defensive checks with no visible signal for whether the guarded case is real. Trace for a findable guarantee before trusting a glance.

## Essential Versus Accidental Complexity, and Why the Split Matters

Fred Brooks split software difficulty into two kinds in "No Silver Bullet" (1986). **Essential complexity** comes from the conceptual structures the problem itself requires. If a program legitimately needs to do thirty different things, those thirty things are essential and cannot be simplified away without failing to solve the problem. **Accidental complexity** comes from the difficulty of representing that structure in a given language, tool, or style, not from the problem. It can be removed without changing what the software does for anyone.

The classification test is not "does this look complicated." It is whether the case a piece of code guards against can actually occur, or whether the code is re-verifying something already guaranteed elsewhere.

```ts
function handleRequest(user: User) {
  // user is guaranteed non-null by getCurrentUser(), which throws otherwise
  if (user == null) { /* ... */ }   // accidental: this case cannot occur here
}

function importUser(payload: unknown) {
  if (!isValidUserPayload(payload)) { /* ... */ }  // essential: payload came from an external caller
}
```

The split also gives a cost/benefit asymmetry worth acting on. Essential complexity's cost buys real protection against a case that can actually happen. Accidental complexity's cost buys nothing, since the case it guards against does not occur. That asymmetry, not aesthetic preference, is why accidental complexity is the priority target when time is limited. It is pure cost with no return, while essential complexity's cost at least purchases the capability the software exists to provide.

## Why the Cost Lands on Change, not on Reading

Reading a function does not require certainty. You can stop once you get the gist and move on. Changing a function safely requires the opposite. You must find every execution path the change could affect, or risk breaking something you never saw. That completeness requirement is what John Ousterhout calls **cognitive load**, how much you must hold in your head to safely complete a task, and **unknown unknowns**, not knowing which pieces of code need to change or what you would even need to know to find out. Ousterhout ranks unknown unknowns the worst of complexity's symptoms, alongside **change amplification** (a simple conceptual change requires touching code in many places), because there is no way to know you have a problem until it bites.

The reason reading does not hurt is **obscurity**. Nothing about a check's surface tells you whether it guards a real case or a dead one. A defensive null check on an impossible case and a load-bearing one on a real case are syntactically identical. Only tracing the actual guarantee resolves the difference, and tracing is exactly the completeness work that reading does not require.

## Complecting, When Two Simple Things Become One Expensive One

Rich Hickey, in "Simple Made Easy" (2011), derives *simple* from the Latin *simplex*, one fold, meaning not interleaved with other things. **Complecting** is what removes that property, braiding two things together that did not need to be joined.

Take a function that both validates business rules on an invoice and builds the HTML string to display it. Each half is genuinely simple in isolation, nothing defensive or convoluted about either one. The cost appears the day one concern needs to change without the other, say a nightly batch job needs the validation logic with no HTML involved at all. Every caller of the combined function now has to be found and updated to use the split version. See [[software-design/splitting-responsibilities]] for the vocabulary, connascence, to measure how far that coupling reaches once it is pulled apart.

## Guarantee Ownership at the Trust Boundary

A guarantee, that some case cannot occur, is only real if someone is responsible for keeping it true. The natural owner is whoever controls the boundary where the data enters the system, an external API caller, user input, a third-party webhook. Inside that boundary, if you control every step from where a value is created to where it is consumed, the guarantee only needs establishing once. Re-verifying it at each downstream call site does not add protection, since the boundary already did that work. It just adds accidental complexity for no return.

This is the same non-redundancy principle behind Design by Contract. See [[software-design/reading-code-for-intent]] for the fuller vocabulary, preconditions, postconditions, and asymmetric blame, that names this precisely. A function should not re-check its own precondition once a caller already guarantees it.

## Triaging Defensive Checks, Especially in AI-generated Code

Since a check's shape gives no visual signal, "this looks obvious" is not evidence, especially for machine-generated code, which pattern-matches "defensive code looks careful" without modeling whether the guarded case is real. See [[software-design/judging-abstractions]] for the related comprehension-debt and lost-provenance failure modes in reviewing AI output generally.

A usable triage rule follows from the ownership argument above. Trace outward from the check for a nearby, concrete, code-level guarantee, a type, a thrown validation, an earlier check in the same call chain, that makes the guarded case provably impossible. Find one quickly, and the check is accidental, safe to remove. Find nothing within a reasonable radius, and you do not yet know. The absence of a guarantee is not evidence of safety.

That triage cost also gives a delegation rule. Verification cost does not shrink because an agent wrote the code. Delegate the parts where the guarantee is cheap to verify, mechanical, locally traceable work. Write the parts yourself where establishing the guarantee is expensive, since an agent producing that code does not remove the tracing work, it only defers it to your review.

## Tradeoffs and Gotchas

- Engineers often label unfamiliar code "accidental complexity" too quickly, without the historical or organizational context that would show it is essential to a constraint they do not know about. (single-voice, Ian Duncan)
- The **incomplete migration trap**: a system mid-transition between two designs carries both the old and new overhead plus the glue between them, a complexity pathology outside the classic essential/accidental split. The fix Duncan argues for is budgeting novelty conservatively and finishing migrations rather than leaving them half done. (single-voice)
- Brooks wrote in 1986 that most accidental complexity of that era, hand-tuned assembly, manual memory layout, had already been absorbed by higher-level languages and tooling, which is why no single technique since has produced another tenfold productivity jump. Treat this as a claim about the state of tooling in 1986, not a law that no accidental complexity remains today. (consensus)

## Related Concepts

- [[software-design/reading-code-for-intent]]: names the exact anti-pattern, a function re-checking its own precondition, that this page frames as accidental complexity with no return.
- [[software-design/judging-abstractions]]: comprehension debt and lost provenance are why AI-generated code is broadly harder to review, complementing the triage rule here.
- [[software-design/splitting-responsibilities]]: connascence measures the coupling that complecting creates once two things get pulled apart again.

## References

- [No Silver Bullet: Essence and Accidents of Software Engineering (Brooks, 1986)](https://worrydream.com/refs/Brooks_1986_-_No_Silver_Bullet.pdf): the source paper defining essential and accidental complexity.
- [No Silver Bullet](https://en.wikipedia.org/wiki/No_Silver_Bullet): encyclopedic summary and reception of Brooks' argument.
- [A Philosophy of Software Design, 2nd edition](https://www.befreed.ai/book/a-philosophy-of-software-design-2nd-edition-by-john-ousterhout): summary of Ousterhout's book, defining complexity as dependencies plus obscurity, with three symptoms, change amplification, cognitive load, and unknown unknowns.
- [Simple Made Easy (Hickey, 2011), transcript](https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/SimpleMadeEasy-mostly-text.md): the simple-versus-easy distinction and complecting.

**Practitioner / opinion:**

- [When is complexity accidental? (Duncan, 2025)](https://www.iankduncan.com/engineering/2025-05-26-when-is-complexity-accidental): the incomplete-migration trap and the case for a conservative novelty budget.
