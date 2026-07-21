---
title: Delegating to agents without losing the map
aliases:
- comprehension debt
- delegation boundaries
- context-switch tax
- agentic engineering
tags:
- software-design
- complexity
- ai-agents
created: '2026-07-03'
updated: '2026-07-03'
source_skill: study-walkthrough
probe_sections:
- Why fast feedback from delegating is addictive
- What passive delegation costs, the map you stop building
- The context-switch tax that undoes parallel delegation
- A checkpoint rule, read and test before starting the next thread
- Tradeoffs and gotchas
last_probed:
- Why fast feedback from delegating is addictive
- What passive delegation costs, the map you stop building
- The context-switch tax that undoes parallel delegation
- A checkpoint rule, read and test before starting the next thread
- Tradeoffs and gotchas
flashcard_ids:
- cmruqtz2l0006qo0mqs7euwx0
- cmruqu0wr0007qo0morqmixps
review_interval: 3
next_review: '2026-07-06'
---

# Delegating to agents without losing the map

Delegating to an AI agent removes the requirement to hold a system's state in your head while you work. That relief is real, and it is also why the pull toward agents can feel closer to a dependency than a tool choice. Once code appears from a prompt, going back to writing it by hand can start to feel painfully slow. This page collects what that relief actually costs, and a few field-tested boundaries for keeping it in check.

## TL;DR

- Code generation outpaces comprehension by roughly an order of magnitude, and a passing test suite gives false confidence, since it says nothing about behaviors nobody thought to test.
- The comprehension drop measured in practice was not from AI use itself. It came from **passive** delegation, accepting output without interrogating it. Active, question-driven use did not show the same drop.
- Parallel agent threads look like a pure speed win on paper, but each thread still needs a human to reload its context before reviewing it. That reload cost tends to cancel out the apparent time saved.
- A workable floor. Do not open a second feature or a second agent thread until you can read through the current change and run its tests yourself.

## Why fast feedback from delegating is addictive

Code volume outruns understanding volume by roughly an order of magnitude. Addy Osmani puts rough numbers on it. AI can generate on the order of 140 to 200 lines of code per minute, while a human comprehends something closer to 20 to 40 lines per minute in the same span. That gap compounds silently, because a green test suite gives no signal about the behaviors nobody wrote a test for, so confidence rises even as real understanding falls behind.

## What passive delegation costs, the map you stop building

An Anthropic study Osmani cites found AI-assisted developers scored 17 percentage points lower on codebase comprehension quizzes than developers who wrote the code themselves, worst specifically on debugging tasks. The gap was not universal, though. Developers who engaged with the AI actively, asking why a piece of code works, probing tradeoffs, requesting walkthroughs, did not show the drop. Passive delegation, accepting output without interrogating it, was the actual driver, not AI use itself.

See [[software-design/judging-abstractions]] for the review-specific version of this cost, lost provenance and why AI-generated seams are harder to catch, and [[software-design/software-complexity]] for why a working diff carries no signal about whether it hides accidental complexity.

## The context-switch tax that undoes parallel delegation

Running several agent threads in parallel looks like a pure speed win on paper, three features advancing at once instead of one. In practice each thread still needs a human to reload its context before reviewing or steering it, and that reload is not free. The tax shows up as the same minutes spent re-orienting to thread B that were supposedly saved by not waiting on thread A, and it recurs every time attention switches back. The apparent parallelism gain and the real context-switch cost tend to cancel out, which is why practitioners who do this for a living converge on small, sequential, human-directed steps over large autonomous or parallel runs. [Simon Willison describes exactly this shape](https://simonw.substack.com/p/agentic-engineering-patterns): hundreds of small steered prompts rather than one large parallel run, specifically to keep review cost bounded.

## A checkpoint rule, read and test before starting the next thread

A workable boundary follows from the tax above. Do not open a second feature or a second agent thread until you can read through the current change and run its tests yourself. This is not a claim that reading and testing catch everything, Ousterhout's unknown unknowns and the obscurity point on [[software-design/software-complexity]] still apply. It is a floor, a minimum act of engagement that keeps the map current before it goes stale.

Willison's related practice follows the same shape. Request a structured walkthrough of anything vibe-coded before trusting it, and keep automated tests non-negotiable, written before generation when possible, so the check exists independent of whether you remember to run it manually. The mechanism worth naming is this. It is not about slowing down for its own sake. The context-switch tax above means the seemingly fast parallel path is frequently not actually faster once the reload cost is counted, so the checkpoint and the speed argument point the same direction.

## Tradeoffs and gotchas

- Willison and Osmani argue full delegation is fine if verification, tests, specs, structured walkthroughs, stays in place and engagement is active rather than passive. Other practitioners, Max Woolf among them, go further and reserve specific categories of work for manual writing regardless of how good the tooling is, treating the boundary as a hard category rather than only a rigor question. (contested)
- Handing an agent bounded, well-scoped tasks, the way you would hand a junior engineer a ticket, plus review, is a recurring practitioner pattern. The durable human skill in that pattern is task decomposition and checkpoint design, not prompting technique. (consensus, recurring across multiple 2026 practitioner threads)
- Comprehension debt compounds. Debt taken on by accepting one unreviewed abstraction, in Osmani's framing, is paid later by whoever builds on top of it, often the same person, with less context than they have right now. (single-voice framing, widely cited)

## Related Concepts

- [[software-design/software-complexity]]: a working diff carries no signal about whether it hides accidental complexity, the same obscurity problem underlies why passive delegation feels safe when it is not.
- [[software-design/judging-abstractions]]: comprehension debt and lost provenance, the review-specific cost of the same passive-delegation pattern.

## References

- [Comprehension debt](https://addyosmani.com/blog/comprehension-debt/): defines the term, the generation-versus-comprehension speed gap, and the Anthropic study distinguishing active from passive AI use.
- [The 80% problem in agentic coding](https://addyo.substack.com/p/the-80-problem-in-agentic-coding): AI reliably solving the first 70 to 80 percent of a problem, and where human judgment has to concentrate on the rest.
- [Agentic engineering patterns](https://simonw.substack.com/p/agentic-engineering-patterns): reviewing every line while AI accelerates typing, small steered prompts over large autonomous runs, and TDD as a non-optional check.

**Practitioner / opinion:**

- [How I use AI agents for programming, mostly (Woolf)](https://minimaxir.com/2026/02/ai-agent-coding/): delegating only within domains you can evaluate even if you cannot implement them, and reserving specific categories of work for manual writing regardless of tooling quality.
