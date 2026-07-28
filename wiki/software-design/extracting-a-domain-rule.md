---
title: Extracting a domain rule
aliases:
- tell dont ask
- law of demeter
- information expert
- extract method
- tests as documentation
tags:
- software-design
- code-review
- coupling
created: '2026-07-21'
updated: '2026-07-21'
source_skill: study-walkthrough
flashcard_ids:
- cmruqe38w0000qo0m3plgjvt6
- cmruqe6da0001qo0mj1zcggx0
- cmruqe9fe0002qo0mx0jabxcf
- cmruqebt50003qo0mufs2q74k
review_interval: 3
next_review: '2026-07-24'
---

# Extracting a domain rule

When an inline compound condition encodes a real rule, the question is not "model or controller" but whether the rule gets a name, a home, and a test. This page uses one refactor, a report-download authorization check, to work through why extracting a named predicate is better, and when it is only ceremony.

## TL;DR

- **Extracting for a name is legitimate at one use.** That is a different decision from extracting for reuse (DRY), which waits for the Rule of Three. A single-use named predicate is not "extra indirection."
- **One boolean can carry two distinct flaws.** Law of Demeter objects to reaching through a foreign object's internals (coupling). Tell, Don't Ask objects to pulling state out to decide externally (encapsulation).
- **A rule belongs on the Information Expert**, the object that already holds the most of the data it needs, so the whole rule fits in one place and only genuinely external data is passed in.
- **Moving a method fixes Demeter only if every hop lands on a direct component** or the collaborator's own public method. If the extracted body still reaches through a foreign chain, you relocated the coupling, you did not remove it.
- **Coverage is not documentation.** Integration coverage proves the code ran. A unit test on the named predicate is an executable specification of the rule. They prove different things.

## Extract for a name, not for reuse

Extracting for a *name* and extracting for *reuse* are different decisions with different thresholds ([[software-design/judging-abstractions]] covers the split). Only reuse (DRY) waits for the Rule of Three. Naming is legitimate at a single call site.

The report-download check has exactly one caller, so the objection "this just adds indirection for a concise controller" silently applies the reuse threshold to a naming decision. The payoff was never shared code. It is a named rule the controller can call without knowing how the rule is computed, and since Extract Function and Inline Function are exact inverses, the decision is reversible, not a commitment.

```ruby
# before: the rule is inline in the controller, unnamed
membership.user_id == user_id &&
  membership.admin? &&
  membership.organization == mail.archived_report.consumption_period.organization
```

```ruby
# after: the rule has a name, on the object that owns the data
if mail.downloadable_by?(current_user)
```

## Tell, Don't Ask vs Law of Demeter

The two principles are often lumped together, but they fault the same line for different reasons.

**Law of Demeter** (coupling). A method may only message its own object, its arguments, objects it creates, and its direct components. The chain `mail.archived_report.consumption_period.organization` sends messages to the *return values* of earlier calls, reaching through two objects the controller has no business knowing. That is the violation.

**Tell, Don't Ask** (encapsulation). Even with no chain, asking the mail for its membership and report and then deciding externally pulls behavior away from the data it operates on. The fix is to tell the mail what you want to know, `downloadable_by?`, and let it decide.

They overlap but are not the same. A call can satisfy one and violate the other. Demeter restricts *which objects you message*; Tell, Don't Ask restricts *pulling state out to decide elsewhere*.

> [Note] Both are heuristics, not laws. Fowler treats Tell, Don't Ask as a guideline and keeps legitimate query methods. In his words, "good design is all about trade-offs."

## Information Expert decides where it lives

GRASP's Information Expert assigns a responsibility to the class that already holds the data to fulfill it. The rule needs three facts, the membership's user, the membership's `admin?` flag, and the report's organization.

```ruby
# app/models/billing/consumption_report_mail.rb
def downloadable_by?(user)
  membership.user == user &&
    membership.admin? &&
    membership.organization == archived_report.organization
end
```

The mail holds both the membership (user, `admin?`) and the archived report (organization), so it is the only object that can express the whole rule. Putting the predicate on `ArchivedReport` instead is weaker, because the report knows only its own organization, not the membership. It would have to accept `membership` as an argument, and the `user ==` identity check would leak back into the controller, splitting one rule across two files. The rule lands where the most of its data already lives.

## A real Demeter fix vs relocating the coupling

Moving a method does not automatically fix a Demeter violation. Copeland's critique is that extraction often just relocates it.

```ruby
# still a violation: this method body reaches through two strangers
def country_code
  address.country.code
end
```

The test is not "is the chain shorter." It is "does every hop land on a direct component or the collaborator's own public method." In the refactor, `downloadable_by?` calls `archived_report.organization`, and that works because of a delegate on the report:

```ruby
# app/models/billing/archived_report.rb
delegate :organization, to: :consumption_period
```

Now trace the hops. The mail messages `archived_report`, its own direct component. `ArchivedReport` reaches into `consumption_period`, *its* own direct component, inside its own class. No single class reaches through a foreign object anymore, and the mail's body never even names `consumption_period`. That is what makes it a real fix rather than a shuffle. The delegate moved the reach into the class that owns the data.

## Coverage is not documentation

The original argument was that extensive integration tests give better coverage on a critical path, so a unit test is redundant. Grant the first half completely. Integration tests *are* the better coverage of that path, and nothing here proposes dropping them. The error is the word "redundant." A unit test on the predicate is not a weaker coverage tool competing with them. It is not a coverage tool at all, it answers a different question. The two roles:

- **Coverage** proves the code executed. 100% of the auth branch can be covered while the rule stays buried in two-phase-login, token, and redirect setup.
- **Documentation** is what a named predicate plus a focused unit test provides. The assertions read like the rule's specification, in isolation, with no request scaffolding.

```ruby
test('#downloadable_by? is true for the owning user who is an admin of the report organization') do
  assert(mail_for(memberships(:superuser_as_admin_in_a)).downloadable_by?(users(:superuser)))
end
```

They are not substitutes. The unit test documents the rule, the integration test proves the wiring (the redirect target, the session, the token). A reviewer asking "what makes a report downloadable?" reads three assertions, not a request spec.

## When extraction is ceremony, not a fix

The "just indirection" instinct is right in a bounded set of cases. An extraction earns its keep only when it names a real domain concept and reduces coupling. It is ceremony when:

- **It fragments the rule.** Half the check stays in the controller, half in the model. The boundary is incoherent and the reader must assemble the rule from two places.
- **It fabricates a home when a better expert exists.** A new class or a predicate on the wrong object, when an object already holds the data.
- **It is a trivial passthrough.** A wrapper that renames a single call, adds no intent, and reduces no coupling.
- **It relocates rather than removes.** The extracted body still reaches through a foreign chain, as in Copeland's case above.

The name test catches most of these. If you cannot give the extracted thing a clear, honest domain name, the boundary is wrong (see [[software-design/judging-abstractions]]).

`downloadable_by?` passes on both counts. It names a real rule, and it reduces coupling in a concrete way. Before, the controller reproduced the rule's logic, the org-equality sequence, so any change to the rule forced a matching change in the controller. That is connascence of *algorithm*, a strong form. After, the controller only has to agree on what the method is *called*. That is connascence of *name*, the weakest form. The refactor reads two ways at once, and they agree. As coupling, it is the connascence strength reduction just described. As responsibility, it removed a reason-to-change from the controller, which had been answering to two actors, transport and authorization policy, so the rule now has a single home. That is equally an SRP win (see [[software-design/splitting-responsibilities]]), because connascence measures the very cohesion SRP is about. The one caveat is narrow. Co-editing both classes to add a feature like this is not an SRP violation, since reasons-to-change are the test, not which files you touch.

## Tradeoffs and gotchas

- **These are heuristics, not laws.** Their own authors say so. Fowler calls Tell, Don't Ask a guideline and warns against dogmatic use, and Lieberherr frames Demeter as a style suggestion. Mechanical application does more harm than good. (consensus)
- **Do not dot-count.** Demeter forbids depending on a returned collaborator's internal structure, not multiple dots. Fluent and query-builder chains (ActiveRecord scopes) return the same type and are fine. Blindly adding wrapper delegators to kill dots can worsen the design. (consensus)
- **The data-structure exception.** Copeland argues Demeter and Tell, Don't Ask should not apply to plain data structures. Chaining through stable data relationships is benign, and applying the rule there breeds pass-through cruft. (contested)
- **Information Expert can bloat a class.** Larman intends it weighed against Low Coupling and High Cohesion, not applied in isolation. Piling every rule onto the expert object can produce a god object. (consensus)

## Related Concepts

- [[software-design/judging-abstractions]]: the two motives for extraction, the Rule of Three, and the name test.
- [[software-design/splitting-responsibilities]]: connascence as the vocabulary for "the controller no longer replicates the rule's algorithm," and why this is coupling reduction rather than SRP.
- [[software-design/reading-code-for-intent]]: a method name is part of its contract, which is why `downloadable_by?` must answer exactly the question it names and nothing more.

## References

- [Law of Demeter (Lieberherr)](http://www.ccs.neu.edu/home/lieber/LoD.html): the canonical formulation, origin, and the immediate-friends rule.
- [TellDontAsk (Fowler)](https://martinfowler.com/bliki/TellDontAsk.html): definition, the Hunt and Thomas attribution, and the trade-offs caveat.
- [Extract Function (Refactoring catalog)](https://refactoring.com/catalog/extractFunction.html): extract and inline as exact inverses, and separating intention from implementation.
- [GRASP Information Expert](https://en.wikipedia.org/wiki/GRASP_(object-oriented_design)): the responsibility-assignment definition, weighed against coupling and cohesion.

**Practitioner / opinion:**

- [Law of Demeter (Ruby Science, thoughtbot)](https://thoughtbot.com/ruby-science/law-of-demeter.html): Rails-flavored extraction of testable domain predicates.
- [Law of Demeter creates more problems than it solves (Copeland)](https://naildrivin5.com/blog/2020/01/22/law-of-demeter-creates-more-problems-than-it-solves.html): the relocation critique and the data-structure exception.
- [The humble extract method (Fernandez)](https://hceris.com/the-humble-extract-method/): extraction as a readability tool and naming difficulty as a design signal.
