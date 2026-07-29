---
title: Reading beyond the diff
aliases:
- blast radius
- action at a distance
- review scope
tags:
- software-design
- code-review
created: '2026-07-24'
updated: '2026-07-24'
source_skill: study-walkthrough
last_deepened: '2026-07-24'
flashcard_ids:
- cmryjbp5600004a0mvoh3k398
- cmryjbr2d00014a0mqbyls1e7
- cmryjbszm00024a0mleqwrfsr
- cmryjbulo00034a0mxj33riwf
review_interval: 3
next_review: '2026-07-27'
---

# Reading beyond the diff

A diff shows the lines you changed. Whether those lines are correct, and whether they leave the surrounding code healthier than they found it, is usually decided by code the diff does not display. This page is about how far past the touched lines to read, why that reading is the work rather than an extra, and how to spend a finite attention budget on it. Its sibling [[software-design/reading-code-for-intent]] covers reading the changed lines for their contract. This page covers reading the code around them.

## TL;DR

- **Comprehension is not optional, it moved.** Hand authoring paid for understanding as you navigated. An agent writes the diff without that step, so the understanding is now a separate act someone has to perform.
- A partially adapted shape is often **worse than the code you started with**, because a later reader has to hold both the old model and the half finished new one at once.
- Two failure classes. **In file coupling** is caught by reading the whole touched file. **Action at a distance** (global hooks, callbacks, default scopes, middleware) cannot be, because nothing in your diff references it.
- **Read by blast radius, not by diff size.** These defects are rare overall and cluster in high fan out code. A finite comprehension budget makes reading everything counterproductive, so aim the depth where being wrong is expensive.
- **Green tests are the loudest read wider signal.** An implicit contract that no test encodes fails silently, so a passing suite is not evidence of correctness for that class of change.

## Comprehension Debt

When you edit code by hand you pay a comprehension cost as you go. You cannot change a method you have not located, and you cannot locate it without reading enough of the surrounding code to know where you are. That reading is a byproduct of authoring, so you rarely notice paying for it.

An agent produces the diff without navigating. The cost did not disappear, it went unpaid, and it sits as debt until a human reads the result. Review is where that debt comes due. This reframes the tension between shipping and reading every detail. The review time reading is not extra nitpicking layered on top of the work. It is the same comprehension the author used to do, relocated to a later moment and a different person.

The debt has a second edge. Shipping a locally correct diff can still lower the health of the code, because a change that adapts one place but not the places that depend on it leaves a **half adapted shape**. A reader now has to reconstruct both the old design and the incomplete new one. That is more confusing than either the original or a fully finished change, even when every touched line is individually correct.

## Two Failure Classes

Not all "read around the change" problems are the same, and the distinction decides which technique catches them.

**In file coupling.** One structure is read by several call sites in the same file, so a local edit ripples to places the diff does not highlight. A real example. A Rails model registered sortable columns in an `order_mapping` hash, and that hash had four consumers in the one file. It resolved the sort column, it built the sortable allow list, it built the readable allow list, and its values were interpolated into filter SQL.

```ruby
# orderable.rb
def mapped_column_name(column)
  raise("Invalid column #{column}") unless orderable_columns.include?(column)
  order_mapping.fetch(column, "#{quoted_table_name}.#{column}")
end
```

Deleting one key looks safe in the diff. It is not, because three other call sites read that hash. **Reading the whole file, rather than the few lines the diff shows, catches this class every time.**

**Action at a distance.** The dependency runs between files, and nothing in the code you touched points at the thing that breaks. A mail interceptor registered globally filtered out expired recipients. Every mailer inherited that behavior, including one case where sending to an expired recipient was intended. No test failed, and nothing in the mailer referenced the interceptor. A documented parallel is the Vanna PR 951 autocommit bug, where a new database write path looked correct in the diff, but whether its writes committed was decided by connection setup in a file outside the diff. The two disagreed, and data was lost silently.

Reading the whole touched file does nothing here, because the interceptor is not in the touched file and there is no reference to follow to it.

## The Blast-Radius Dial

How much surrounding code to read is set by **blast radius**, the fan out of what you touch multiplied by the cost of being wrong. It is not set by the size of the diff. A five line change to a global interceptor deserves far more reading than a two hundred line change to one leaf template.

Three facts make the dial the right tool rather than "read everything".

- **The defects are rare overall.** Most changes are low risk, and in modern review the large majority resolve with at most one comment round. A leaf change rarely hides this.
- **They cluster.** The expensive ones concentrate in high fan out and implicit contract code, such as interceptors, callbacks, `default_scope`, middleware, authorization, money, and migrations. The practitioner summary is that the changes that hurt most are the ones that look safe.
- **Attention is finite.** Review effectiveness drops sharply past a few hundred lines in one sitting, so uniform deep reading is not only slow, it is counterproductive. Spreading the budget everywhere spends it poorly where it matters.

**Green tests are the loudest signal to read wider.** When behavior changed, or is silently constrained, but no test moved, the suite is telling you nothing about the case that will actually break. Both the interceptor and the autocommit bug shared this tell.

## Why Reading More Is not Enough

Reading more of the touched files solves in file coupling. It cannot solve action at a distance, and the reason is an honest limit. **You cannot know to read what is not already in your head.** To decide to open the interceptor you would have to know it exists, and nothing in the change points at it.

So the trigger and the map are two different things, and you need both. The trigger is the blast radius question, "this is consequential, what could go wrong here?". That question returns a blank unless a **map** is in place, a working knowledge of the application's cross cutting layers, the interceptors, callbacks, global scopes, and middleware that act at a distance. Raising ownership on a high blast radius change means going to build that map for the area before shipping, by actively asking what globally registered thing could touch this and then looking.

You will still miss some. That is built into the rule rather than a failure of it. The residue is exactly why **review is the backstop**, a second reader whose map differs from yours, and why turning an implicit contract into a test converts a silent failure into a loud one.

## Chesterton's Fence

Before you delete code, or accept a change that deletes it, establish why it was there. The principle, from G. K. Chesterton, is that you do not remove a fence until you know why it was put up. In code the fence is usually a line that looks pointless, a defensive nil check, an extra transaction, a seemingly redundant mapping, a workaround with no comment.

The safe deletion is not "this looks redundant". It is "I traced why this existed, and that reason no longer holds". Those are two different acts, and the gap between them is the surrounding reading this page is about.

Your own review shows both sides. The comment "why the transaction block if we have `with_lock`?" is a Chesterton's Fence question, not a delete instruction. It asks you to find the reason before removing it. And the identity entries in `order_mapping` were only safe to drop because a fact established elsewhere in the change, a migration that made `name` and `vendor` real columns, removed the reason they existed. Drop the same entries on a branch without that migration and you break sorting, reading, and filtering, because the fence is still load bearing.

## Reading for Absence

Everything above is about reading code that is present. A distinct lens reads for what is missing, because a change is often incomplete not in its lines but in what it fails to include.

Ask what the change implies but does not carry:

- A schema change with no migration, or a migration with no rollback plan.
- A risky change with no feature flag to roll it out gradually or switch it off.
- New behavior or a new edge case with no test that would fail if the behavior regressed.
- A runbook or documentation the change makes stale but does not update.

The related tell is when the story does not add up. When the description says "add logging" but the diff also moves business logic, or a "fix typo" changes a method signature, the mismatch is telling you the real change is not the stated one. Reading for absence and reading the surrounding code are complements. One asks whether what is present is correct in context, the other asks whether what is present is complete.

## A Decision Procedure

A compact routine to run from "here is my diff" to "how much do I read".

1. **Read the whole touched file, not the diff window.** This is cheap and catches in file coupling. Do it every time.
2. **Estimate blast radius.** Ask how many places depend on what you touched and how costly it is to be wrong. A high fan out, shared, security, money, or migration path raises the dial.
3. **On a high reading, build the map.** Ask what acts at a distance on this path, the interceptors, callbacks, global scopes, and middleware, and go read them. Reading here is directed by system knowledge, not by following references out of the diff.
4. **Check the tests for the implicit contract.** If behavior changed but no test did, that is the signal to read wider and to add the test.
5. **Separate reading from changing.** Reading wide is always in scope. Changing wide is not. When surrounding code is worth cleaning up, defer unrelated cleanup to a follow up issue rather than bundling it, unless the cleanup is local and mechanical.
6. **Before removing code, find the reason it exists.** Trace why a line is there before deleting it as redundant (Chesterton's Fence). Safe to remove means the reason is gone, not that the line looks pointless.
7. **Read for what the change omits.** A schema change wants a migration and a rollback, a risky change wants a flag, new behavior wants a test, and a stale runbook wants updating.

Step 5 resolves the opportunistic cleanup tension. The reviewer reading the whole neighborhood is judging health, not demanding you fix the neighborhood in this change.

## Tradeoffs and Gotchas

- **Tier by risk, not by author reputation.** Match review depth to the cost of being wrong, and be aware that most published review advice was written for a very different blast radius than yours, so it can misapply. (consensus)
- **Scope discipline beats opportunistic cleanup in the same change.** The canonical stance is to read the surrounding code to judge the change, but to defer unrelated cleanup to a filed issue with a TODO rather than combine it with the work. Reading wide and cleaning wide are different decisions. (consensus)
- **The comprehension budget numbers are a rule of thumb.** The commonly cited limits trace to a single large industry study, useful as a direction rather than a precise threshold. (contested)
- **A passing suite is not a correctness proof for implicit contracts.** Idempotency, ordering, cache and database consistency, and concurrency are rarely encoded in tests, so a fully covered change can still ship an incident. (consensus)

## Related Concepts

- [[software-design/reading-code-for-intent]]: reading the changed lines for their contract, the sibling to reading around them. Review is the backstop on both pages.
- [[software-design/delegating-to-agents-without-losing-the-map]]: the agent-authoring side of comprehension debt, and keeping the map when you did not navigate the code yourself.
- [[software-design/software-complexity]]: a half adapted shape is complexity added, the change amplifier and cognitive load view of the same harm.
- [[angular/where-code-belongs]]: deciding where a change belongs is the authoring side of judging blast radius.
- [[software-design/judging-abstractions]]: a wrong abstraction boundary is where action at a distance tends to hide.

## References

- [Google Engineering Practices, What to look for](https://google.github.io/eng-practices/review/reviewer/looking-for.html): read the whole file and consider the change in the context of the system, and defer unrelated cleanup to a bug plus TODO.
- [Google Engineering Practices, The Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html): review defends overall code health, not only line level correctness.
- [Modern Code Review, a case study at Google (Sadowski et al.)](https://research.google/pubs/modern-code-review-a-case-study-at-google/): review is comprehension first, and effectiveness degrades past a mental model budget.
- [SmartBear on the Cisco peer review study](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/): the origin of the two hundred to four hundred line and rate of review numbers.

**Practitioner / opinion:**

- [Addy Osmani, agentic code review](https://addyosmani.com/blog/agentic-code-review/): review depth as a dial set by blast radius, and a diff ordered by file rather than for comprehension.
- [Beyond the diff, and Vanna PR 951](https://jetxu-llm.github.io/posts/beyond-the-diff-llamapreview-catches-critical-bug/): the autocommit bug visible only in a file outside the diff.
- [GitHub discussion on when to review deeper](https://github.com/orgs/community/discussions/184556): implicit contract changes and the "3 AM test" drive depth, not diff size.
- [Chesterton's Fence](https://en.wikipedia.org/wiki/G._K._Chesterton#Chesterton's_fence): the origin of "do not remove a fence until you know why it was put up".
