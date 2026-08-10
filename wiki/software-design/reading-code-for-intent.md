---
title: Reading code for intent
aliases:
- design by contract
- principle of least astonishment
- pit of success
- make illegal states unrepresentable
- preconditions and postconditions
tags:
- software-design
- code-review
- contracts
- legacy-code
created: '2026-07-02'
updated: '2026-08-10'
source_skill: study-walkthrough
flashcard_ids:
- cmr3mfpvn000avi0mwndjb23g
- cmr3mfu74000cvi0mp1wy11c5
- cmsnp5cgz0000fg0msajjyd08
---

# Reading code for intent

Most subtle review misses are not logic bugs. They are intent mismatches. The code runs, the tests pass, and it still uses a system in a way it was not meant to be used, or surprises the next caller. This page is the vocabulary for reading and writing code against its intended contract, so "this feels off" becomes a precise comment. It sharpens the eye that catches the defects types and tests let through.

## TL;DR

- A **signature is a contract**. `getUser(id): User` promises a `User` on every return. If it can return nothing, the type lies and callers cannot know to guard.
- A contract has two sides. **Preconditions** the caller must meet, **postconditions** the function guarantees. A broken precondition blames the caller; a broken postcondition blames the callee.
- The **name is part of the contract** (Principle of Least Astonishment). A method that does more than its name says is a defect even when it works.
- Types are honest about returns and tests assert only expected behavior, so **hidden-intent defects need a human**. Review is the backstop.
- Fixes climb a ladder: **document, fail loud, make impossible**. Push misuse toward a compile error (make illegal states unrepresentable, the pit of success).

## The Signature Is a Contract

A type signature is a promise. In a codebase where a user sometimes does not exist:

```ts
function getUser(id: string): User   // promises a User on every return
```

A caller trusts the promise and writes `sendEmail(getUser(id).email)`. When the user is missing, the value is `undefined`, and the caller crashes at a line that looks correct. The bug is not in the caller. It is in the signature, which hid a case the caller had no way to know about. The honest version forces the truth into the open:

```ts
function getUser(id: string): User | undefined
```

Now the compiler makes every caller confront the missing case. Reading for intent starts here. **Read the signature as a set of promises, then check whether the body keeps them.**

## Preconditions, Postconditions, and Asymmetric Blame

Design by Contract (Bertrand Meyer, from Eiffel) models an interface as a contract with three assertions:

- **Precondition** (`require`): what must hold *before* the call. The caller's obligation.
- **Postcondition** (`ensure`): what the function guarantees *on normal return*. The callee's obligation.
- **Invariant**: what stays true before and after every public method. The object's obligation.

The powerful part for review is **asymmetric blame**:

- A broken **precondition blames the caller**. `sqrt(-1)` when the contract said `x >= 0` is the caller's bug.
- A broken **postcondition or invariant blames the callee**. `getUser(): User` returning `undefined` is the function's bug.

Map a failure to whichever side of the contract broke and the "whose bug is this?" argument resolves itself. Contracts are also documentation that cannot drift, because you read intended usage off the `require`/`ensure` clauses rather than stale prose.

> [Note] Design by Contract is the offensive inverse of defensive programming. By Meyer's non-redundancy principle a function must NOT re-check its own precondition. Double-guarding is an anti-pattern, not extra safety, because it blurs whose obligation the check was.

## The Name Is Part of the Contract

Not all of the contract is in the types. The **name** sets the caller's mental model, and violating that model is the **Principle of Least Astonishment** breach.

```ts
user.hasPermission('edit')   // returns boolean, and also writes an audit-log row
```

The return type is an honest `boolean`. Tests pass. Yet the name promises a *question*, so the only reasonable expectation is "I get an answer and nothing changes." The hidden write betrays that. Calling it twice double-logs, and calling it in a log line or debugger silently mutates data. A name that promises a query must not command (this is command-query separation seen from the intent side, see [[software-design/splitting-responsibilities]]). Astonishment is relative to the audience's existing mental model, so the test is "what would a competent caller reading this name assume?"

## Why Review Is the Backstop

This defect class is invisible to the tools:

- The **type** is truthful about the return value and says nothing about side effects.
- **Tests** assert expected behavior. Nobody writes a test that `hasPermission` does *not* touch the database, because the name already implied it would not.

So the gap sits exactly where expectation and reality diverge silently, and only a human reading the implementation against the name and signature closes it. This is why intent review is a distinct skill from testing, and why "the obvious use should be the correct use" is a review standard, not a nicety. Practitioners are blunt about it. Developers will not read a manual to learn an API's real behavior, so surprises are caught socially, in review, or not at all.

## The Ladder from Documented to Impossible

When an API can be misused, the fixes are not equal. Ranked weakest to strongest:

1. **Document** the precondition in a comment or doc. Caught *never*, only if a human reads and remembers it.
2. **Fail loud** with an assert or thrown error on misuse. Caught at runtime, but only when the bad path actually executes.
3. **Make it not compile** by changing the types. Caught at compile time, and impossible to ignore.

The axis is *when misuse is caught* and *how little it relies on the human choosing correctly*. Climbing it is **"make illegal states unrepresentable"**, pushing enforcement into the type system (a `User | undefined`, a discriminated union, a `PostId` nominal type that cannot be swapped with a `PostTitle`). The design goal of landing everyone in correct usage by default is the **pit of success**. Easy to do right, hard to do wrong. The reviewer's upgrade is to stop at "this could be misused" and instead ask "can we move this up the ladder?" And when you cannot reach compile-time (level 3), reach for loud failure (level 2). Silent tolerance of a contract violation is the worst option.

## Changing Inherited Code

Reading for intent asks whose obligation a given assertion is. Changing inherited code asks a sharper question. Whose obligation am I about to move, and does the new owner actually meet it?

Take a method you did not write:

```ruby
def archive_order(order_id)
  order = Order.find(order_id)             # blows up if absent
  raise ArgumentError, "no shipment" unless order.shipment
  order.update!(archived: true)
end
```

The two guards look like defensive noise once you notice the callers already load the order and check the shipment. So you simplify:

```ruby
def archive_order(order)
  order.update!(archived: true)
end
```

The constraint did not go away. It changed owner. What was enforced inside the callee is now a **precondition every caller must establish**, and the signature does not say so. It got shorter, not more honest. Nothing marks the one callsite that loads the order but never looks at the shipment.

The failure mode gets worse in the direction that matters. Before, a shipment-less order raised at the boundary, on the first line, with the bad input in the stack trace. After, `update!` succeeds and an archived order with no shipment is persisted. The invariant is broken in the database, and it surfaces later in a report, a nightly job, or a customer complaint, far from the change that caused it. This is the ladder from the previous section walked **downwards**, from level 2 back to level 0, while the diff reads as a cleanup.

The tension with the non-redundancy principle is real but resolvable. Meyer is right that a function should not re-check its own precondition. That licenses deleting the guard only once the precondition is genuinely established by every caller. In legacy code the contract is unwritten, so nothing tells you whether it is. Enumerating the callsites and confirming each one establishes what you are about to stop enforcing **is the work**, not a formality before it. If you cannot finish that enumeration, keep the guard, because a redundant check costs a little clarity and a missing one costs an invalid record.

Two habits follow. Recover the contract before you touch the body, by reading what the method assumes on entry, what it guarantees on return, and what it keeps true about the object. And when you move an obligation outward, make the new signature say so, by taking a type that cannot be constructed in the invalid state or by failing loudly at the new boundary. Silence is the option that turned your refactor into a data bug.

## Tradeoffs and Gotchas

- **Contracts can be stripped in production.** Eiffel and .NET Code Contracts often compile precondition and postcondition checks out of release builds, so a contract that catches misuse in debug can silently permit it once real inputs arrive. Do not assume the assertion runs. (consensus)
- **Least astonishment is audience-relative.** The same behavior astonishes a novice and not an expert, so "obvious" is defined by the intended reader, not in the abstract. (consensus)
- **Illegal-states-unrepresentable has limits.** It is fully achievable only in languages with sum or union types (Rust, F#, TypeScript discriminated unions). Elsewhere it degrades to runtime smart constructors, a weaker guarantee. At scale, some invariants (foreign keys, multi-step state transitions) cannot be encoded in types and still need runtime enforcement. (contested)
- **Validation only in service methods is a false sense of security.** If illegal objects can still be constructed, a later path can build one. Enforce invariants at construction (private constructor plus factory) so the illegal state cannot exist. (consensus)

## Related Concepts

- [[software-design/splitting-responsibilities]]: command-query separation is the same query-must-not-command rule from the responsibility side.
- [[software-design/judging-abstractions]]: a leaky or wrong abstraction is an intent mismatch at the module boundary.
- [[angular/where-code-belongs]]: putting wire-to-domain parsing at the boundary is enforcing a contract at the point data enters.

## References

- [Design by Contract (Eiffel)](https://www.eiffel.com/values/design-by-contract/): the canonical precondition/postcondition/invariant definitions and contract-as-documentation.
- [Applying Design by Contract (Meyer, 1992)](https://se.inf.ethz.ch/~meyer/publications/computer/contract.pdf): the source paper, asymmetric blame, and the anti-defensive stance.
- [Principle of least astonishment](https://en.wikipedia.org/wiki/Principle_of_least_astonishment): history and the audience-relative definition.
- [The Pit of Success](https://ricomariani.medium.com/the-pit-of-success-cfefc6cb64c8): Mariani's origin account of the design goal.

**Practitioner / opinion:**

- [APIs and the principle of least surprise](https://daedtech.com/apis-principle-least-surprise/): war stories of hidden side effects and why review is the remedy.
- [Make illegal states unrepresentable (TS/DDD)](https://khalilstemmler.com/articles/typescript-domain-driven-design/make-illegal-states-unrepresentable/): private constructors, factories, nominal vs structural typing.
