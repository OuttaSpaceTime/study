---
title: Splitting responsibilities
aliases:
- single responsibility principle
- SRP
- command-query separation
- CQS
- connascence
- coupling and cohesion
tags:
- software-design
- coupling
- code-review
created: '2026-07-02'
updated: '2026-07-02'
source_skill: study-walkthrough
last_deepened: '2026-07-02'
flashcard_ids:
- cmr3h5scb0003vi0mlc9rdm2i
- cmr3h5u7c0004vi0mk8acp5vl
review_interval: 8
next_review: '2026-07-29'
---

# Splitting responsibilities

"These responsibilities aren't split right" is a real review instinct that usually comes out vague. This page gives it precise vocabulary. Three lenses (SRP by actor, command-query separation, and connascence) plus the counter-danger of over-splitting. The theme underneath all of them is cohesion. Things that change together should live together.

## TL;DR

- **SRP** measures **actors**, not tasks. A module should be responsible to one actor, a group of stakeholders who request changes. "Does one thing" is a misread.
- **CQS**. A method is either a command (mutates, returns nothing) or a query (returns a value, changes no observable state), never both. Asking a question shouldn't change the answer.
- **Connascence** ranks coupling by **strength**, and weighs it by **locality** and **degree**. Weaken strong coupling, or keep it local.
- **Over-splitting** backfires. Scattering cohesive logic across tiny classes worsens locality and raises total connascence.

## What SRP Actually Measures

The Single Responsibility Principle is widely misquoted as "a class should do one thing." Robert Martin, who named it, explicitly disowns that reading. His precise form is **"a module should be responsible to one, and only one, actor,"** where an actor is a group of stakeholders who request changes. His alternate wording is **"gather together the things that change for the same reasons, and separate those that change for different reasons."** The lineage runs back to Parnas (information hiding, 1972) and Dijkstra (separation of concerns).

So the unit is not the count of methods. It is the count of *reasons to change*.

```python
class Employee:
    def calculate_pay(self):   ...   # Finance owns payroll rules
    def report_hours(self):    ...   # HR owns timesheet policy
    def save(self):            ...   # DBA owns persistence
```

Every method does exactly one thing, yet this violates SRP, because three different actors will demand changes on independent schedules and collide in one file. The canonical failure is accidental coupling. Finance asks for a payroll change, a developer edits `calculate_pay`, and because it shared a rounding helper with `report_hours`, HR's timesheet silently breaks. Different reasons to change were welded together.

The inverse also holds. A class with ten methods that all serve one actor is fine. Count of things is a red herring. Count of actors is the measure.

## Command-Query Separation and CQS vs CQRS

Command-Query Separation (Bertrand Meyer) states that every method is one of two kinds. A **command** changes state and returns nothing. A **query** returns a value and changes no observable state. No method should be both.

The property a query must preserve is repeatability. You can call it any number of times, in any order, without changing anything, so it is safe to drop into a log line, a debugger watch, or an `if` condition. A method like `available?` that also logs the user in has lost that property, and the side effect is invisible at the call site.

Three refinements:

- CQS governs **observable** state. A query caching its result internally is fine, because the caller cannot observe the change.
- **Sanctioned exceptions exist.** `stack.pop()`, `iterator.next()`, and `getAndIncrement()` deliberately mutate and return. The sin is the *hidden, undocumented* side effect, not the deliberate one.
- CQS is method-level (Meyer). **CQRS** (Command Query Responsibility Segregation) lifts the same instinct to the architecture level with separate read and write models, often with eventual consistency. Same idea, different altitude. Do not conflate them.

## Connascence as a Coupling Vocabulary

Connascence (Meilir Page-Jones, 1992) replaces the binary "coupled or not" with a scale. Two components are connascent if changing one forces a matching change in the other to stay correct. Ranked roughly weakest to strongest:

- **Name**. Both must agree something is called `user_id`. Rename tooling fixes it.
- **Meaning / Convention**. Both hardcode `200` to mean "OK." The agreement is invisible.
- **Position**. Both must agree on the order of arguments or steps.
- **Algorithm / Execution order**. Both must run the same steps in the same order. Nothing names the contract, so it breaks silently.

Static forms (visible in the source) are generally weaker than dynamic forms (Execution, Timing, Value, Identity), which surface only at runtime and so are harder to catch. **Strength** is the effort it would take to refactor the coupling away, which tracks how badly a change can bite. Converting a magic `200` into a named constant is literally strength reduction.

## The Operative Rule for Connascence

Strength is only one of three axes. The other two decide whether you actually comment in review.

- **Locality**. How close the coupled elements sit. Two tightly-coupled lines in one small function are fine. The same coupling stretched across two files or two services is far worse, because a change on one end gives no visual reminder of the other.
- **Degree**. How many elements are entangled. Two callers versus two hundred.

The rule you can apply cold:

> Minimize connascence overall. Convert strong forms into weaker ones where you can. Tolerate strong connascence only when locality is high, and weaken it as elements grow more distant across boundaries.

This reframes ordinary review notes. "Extract a constant" is strength reduction. "These two files must always change together" is a locality alarm.

## Over-splitting Can Worsen Coupling

SRP pushes you to separate. Taken too far, that becomes its own failure mode. If you split logic that genuinely changes together (one actor, one reason to change) into five tiny classes, the pieces stay tightly coupled, but now that coupling is spread across five files. You traded a cohesive class for **high strength plus poor locality**, which is *more* total connascence than you started with. A single conceptual change now touches five files, and the behavior is no longer readable in one place.

The reviewer's test for "correctly separated" versus "shattered into confetti". Did the split put a real actor boundary between the pieces, or did it just push tightly-coupled code apart? Cohesion is the counterweight to SRP, and connascence is how you measure whether a split helped or hurt.

## Tradeoffs and Gotchas

- **SRP is under-defined.** It never defines "reason," "change," or "responsibility," so two engineers can cite SRP to justify opposite decompositions. It gives little objective guidance at the exact decision point. (consensus)
- **SRP is retroactive.** An axis of change only becomes visible once changes actually happen, so you often learn the correct split from the second or third change request, not up front. This rhymes with the Rule of Three. (contested)
- **Over-eager SRP is a known smell.** Fragmenting a cohesive domain class into many one-method collaborators scatters logic and raises complexity. The cure can be worse than the coupling. (contested)
- **Connascence ranks are heuristic.** The static-weaker-than-dynamic ordering is stable, but the fine-grained strength rank and naming (Meaning vs Convention) are convention, not a strict standard. Use it to have the conversation, not to score a build. (single-voice)

## Related Concepts

- [[software-design/judging-abstractions]]: the sibling review skill. A wrong abstraction is often several actors' concerns merged behind flags, which is an SRP failure seen from the abstraction side.
- [[rails/delegated-type]]: a worked example of choosing where responsibilities and attributes live deliberately.

## References

- [The Single Responsibility Principle](https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html): Martin's 2014 reframing around actors and reasons-to-change, disowning "does one thing."
- [CommandQuerySeparation](https://martinfowler.com/bliki/CommandQuerySeparation.html): Fowler on Meyer's CQS, observable-state scope, and sanctioned exceptions.
- [Connascence](https://en.wikipedia.org/wiki/Connascence): Page-Jones taxonomy, the static/dynamic ranking, and the strength/locality/degree axes.
- [Single-responsibility principle](https://en.wikipedia.org/wiki/Single-responsibility_principle): encyclopedic summary with the report-content-vs-format example and Parnas/Dijkstra lineage.

**Practitioner / opinion:**

- [Connascence as a vocabulary to discuss coupling](https://thoughtbot.com/blog/connascence-as-a-vocabulary-to-discuss-coupling): using the axes to make decoupling debates concrete.
- [I don't love the Single Responsibility Principle](https://sklivvz.com/posts/i-dont-love-the-single-responsibility-principle): the ambiguity and over-fragmentation critique.
- [CQS when queries should have side effects](https://blog.ploeh.dk/2015/10/08/command-query-separation-when-queries-should-have-side-effects/): CQS reframed as making side effects explicit.
