---
title: Judging abstractions
aliases:
- wrong abstraction
- leaky abstractions
- rule of three
- abstraction boundaries
- premature abstraction
tags:
- software-design
- abstraction
- code-review
created: '2026-07-02'
updated: '2026-07-02'
source_skill: study-walkthrough
flashcard_ids:
- cmr352mhn0000vi0my4yi3fk0
- cmr352oou0001vi0m2ma2kmqz
- cmr352qkt0002vi0mmvsrf7ou
---

# Judging abstractions

The reviewer's hardest calls are not bugs. They are seams. Is this the right abstraction, at the right altitude, or a wrong one that everyone will inherit? This page collects four load-bearing ideas for making that call cold, plus why the call matters more when the code was machine-generated.

## TL;DR

- A shared function that accretes flag parameters and conditionals is the signature of a **wrong abstraction**. Each flag is a caller who reused it because it almost fit.
- The counter-intuitive fix is to **re-inline** the abstraction back into every caller, delete each caller's dead branches, then re-derive the real seam from the now-visible duplication.
- Extract for **sharing** only after the Rule of Three (two or three real instances). Extracting for a **name** is fine at one use. They are different decisions.
- **All non-trivial abstractions leak** (Spolsky). An abstraction saves you time working, not time learning. When it leaks you must understand the layer beneath anyway.
- AI codegen amplifies wrong and premature abstractions, and strips the provenance you would normally use to catch them.

## The Wrong-Abstraction Signal

The signal is not "this function is long" or "this has many `if`s". A parser legitimately branches a lot. The specific tell is **flag or boolean parameters that callers pass in, with the function branching on them**.

```python
# v1, extracted when a second caller appeared. Clean.
def send_notification(user, message):
    deliver_email(render(user, message), user.email)

# v4, six weeks and three more callers later
def send_notification(user, message, sms=False, urgent=False,
                      skip_if_unsubscribed=True):
    if urgent:
        message = "[URGENT] " + message
    if skip_if_unsubscribed and user.unsubscribed and not urgent:
        return
    if sms:
        deliver_sms(render_sms(user, message), user.phone)
    else:
        deliver_email(render(user, message), user.email)
```

Each flag is a fingerprint of a caller who reused `send_notification` because it was there and *almost* fit, then paid the difference with a parameter and a conditional. That reuse pressure is the decay mechanism, not an accident. Sandi Metz names this "the wrong abstraction" and coins the maxim **"duplication is far cheaper than the wrong abstraction."** A wrong abstraction decays predictably. Each near-fit requirement bolts on one more parameter and one more branch until the shared code is condition-laden and nobody can safely change it. Every single step looks locally reasonable, which is why it survives review.

Reviewer's move. When flags accrete through shared code, do not ask "is this flag correct?". Ask "how many *unrelated concerns* have been merged here?". In the example, `sms` is channel, `urgent` is message formatting, `skip_if_unsubscribed` is delivery policy. Three concerns, one function. Splitting by the most visible axis (channel) absorbs only one of them.

## The Remedy Is Re-Inline, Then Re-Derive

Once you have decided the abstraction is wrong, the instinct is to refactor *forward* into a cleaner class hierarchy. That is a trap. The only map you have of "what belongs together" is the tangled function itself, and you already agreed it is distorted. Carving a new design from a distorted template inherits the bad assumptions.

The ground truth of what each caller actually needs lives at the **call sites**, not in the shared function. So go backward first:

1. Inline the shared function body into every caller.
2. At each call site, delete every branch that caller never hits.
3. Read the re-introduced duplication. It shows what each caller genuinely does, unclouded.
4. Extract the correct seam from that, if a seam even exists. You may find it splits into three things, not one.

The barrier is psychological, not technical. The more elaborate and battle-scarred the wrong abstraction is, the harder it feels to delete, because sunk cost misreads complexity as importance. The complexity is the symptom, not the asset.

> [Note] Metz's maxim is conditional. It applies once the abstraction is *proven wrong*. It does not supersede DRY and is not a licence to copy-paste. It bounds when DRY applies.

## Rule of Three and the Two Motives for Extraction

There are two different reasons to pull code into a function, and they have different thresholds.

- **Extract for a name (readability).** Pulling one messy block into a well-named function. Legitimate at a *single* use. You are labeling a step, not abstracting over callers. Cheap, local, reversible.
- **Extract for sharing (DRY).** Hoisting logic that several callers will depend on. This binds every caller. Wait for the **Rule of Three**: two similar instances can stay duplicated, the third is your cue to extract.

The number is not superstition. Three concrete instances give you enough *variation data* to locate the correct seam. Extract from too few examples and you pick a wrong abstraction at the wrong altitude, then every caller inherits that binding as requirements arrive. The wider the dependency fan-in, the more places a wrong seam forces you to touch, and the easier it is to miss one.

A practitioner altitude check from Arpit Bhayani is the **name test**. If you cannot give the extracted thing a clear, honest name, it is not a clear abstraction yet. The Rule of Three is Fowler's popularization in *Refactoring* (1999), attributed there to Don Roberts. It is a heuristic for *when*, not an enforced threshold.

## Leaky Abstractions and the Working-vs-Learning Cost

Joel Spolsky's Law of Leaky Abstractions states that **"all non-trivial abstractions, to some degree, are leaky."** Leaking is not a quality defect. Even a well-chosen abstraction leaks, because it sits on a layer it cannot fully hide.

```ruby
User.active.each { |u| puts u.posts.count }
```

ActiveRecord is a genuinely good abstraction over SQL. This reads clean and passes tests. In production with 10k users it crawls (N+1 queries). To diagnose and fix it you must drop to the SQL layer, and sometimes into the AR source. The abstraction being *well-designed* spared you nothing at the moment it leaked.

That yields the portable cost formula. An abstraction **saves you time working** (writing the low-level calls), but **does not save you time learning** (understanding the layer beneath). The reviewer's corollary. A codebase leaning on an abstraction is only as maintainable as the team's grasp of what is under it. The abstraction hides the layer until the day it doesn't, and that day is usually an incident.

This is independent of the wrong-abstraction idea. The Rule of Three answers *when to extract*. The Law of Leaky Abstractions answers *why no abstraction is ever perfect*. Do not conflate them.

## Why This Bites Harder in AI-generated Code

You said reviewing AI output is where subtle design problems slip past you. Two mechanisms, both reported by practitioners (treat as field observation, not settled law).

**Lost provenance.** A colleague's PR carries context. You saw it evolve, you can ask "why this seam?", you know whether it came from three real cases or one. AI code arrives fully formed with no visible reasoning and no history, so you cannot tell whether the seam was derived from real variation or invented whole. Worse, an LLM extracts an abstraction from the single literal problem in the prompt. That is zero real instances, premature extraction in its purest form, and the reasoning that would let you catch it is invisible.

**Comprehension debt** (Addy Osmani). Reading does not scale with generation. AI emits plausible-looking code faster and in more volume than you can genuinely evaluate, so the equilibrium drifts toward rubber-stamping. A wrong seam approved early cascades through every PR built on top of it. Verification cost is non-linear. The last 20% of correctness, including "is this abstraction at the right altitude", needs the most human attention, so seam judgment stays a human job at architectural decision points.

The defense is boring and real. Slow down specifically at seams. Ask the "couldn't you just...?" question the model never asks itself.

## Tradeoffs and Gotchas

- **The maxim is contested as an absolute.** Jason Swett argues "duplication cheaper than wrong abstraction" is a false binary. He says the better move for an over-fit abstraction is often to **split it into two** rather than re-inline to duplication, and that reluctance to refactor is an organizational symptom (thin tests, unclear ownership) fixable by tests and collective ownership, not by tolerating duplication. This refines the timing heuristic. It does not contradict Metz, whose claim is explicitly conditional on the abstraction being wrong. (contested)
- **Root-cause of the sunk-cost trap.** Metz frames the reluctance to delete as inherent psychology. Swett frames it as an org problem. Both diagnoses are live. (contested)
- **Data structures before abstractions** (Torvalds, via van Beelen). Get the data shape right first. Code is cheap to refactor, a wrong abstraction over the wrong data shape is expensive to swap. (single-voice)
- **Wrapper/DI ceremony.** van Beelen argues many pass-through wrapper classes and class-based DI are ceremony, and a defaulted function parameter gives the same testability seam with less code. Style opinion, no authoritative backing. (contested)

## Related Concepts

- [[rails/activerecord-preloading]]: the concrete fix when the ActiveRecord abstraction leaks into N+1 queries.
- [[rails/delegated-type]]: a worked example of choosing a seam (where attributes live) deliberately rather than by accretion.

## References

- [The Law of Leaky Abstractions](https://www.joelonsoftware.com/2002/11/11/the-law-of-leaky-abstractions/): Spolsky's 2002 essay coining the law, with the TCP/IP example and the working-vs-learning corollary.
- [The Wrong Abstraction](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction): Metz's canonical essay, the decay mechanism, and the re-inline remedy.
- [Rule of Three](https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming)): definition, Fowler/Don Roberts attribution, and the premature-abstraction risk.

**Practitioner / opinion:**

- [Premature abstractions](https://arpit.substack.com/p/premature-abstractions): Bhayani on the name test and AI as a premature-abstraction amplifier.
- [The 80% problem in agentic coding](https://addyo.substack.com/p/the-80-problem-in-agentic-coding): Osmani on comprehension debt and non-linear verification cost.
- [Duplication is cheaper than the wrong abstraction?](https://www.codewithjason.com/duplication-cheaper-wrong-abstraction/): Swett's rebuttal arguing split-into-two over re-duplication.
