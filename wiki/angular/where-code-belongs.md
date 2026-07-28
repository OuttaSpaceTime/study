---
title: Where code belongs
aliases:
- layered architecture
- smart and dumb components
- container and presentational components
- dependency direction
- where code belongs
tags:
- angular
- architecture
- code-review
created: '2026-07-02'
updated: '2026-07-21'
source_skill: study-walkthrough
last_deepened: '2026-07-02'
flashcard_ids:
- cmr3kzoif0005vi0m6saz3h2t
- cmr3kzuq10007vi0ml2cjtub2
- cmr3kzwwp0008vi0macw7zben
review_interval: 4
next_review: '2026-07-25'
---

# Where code belongs

"Where should this go?" is the placement question you answer dozens of times a day, and getting it wrong is what makes a codebase hard to change later. This page turns the gut call into a procedure. It is the Angular-flavoured application of [[software-design/splitting-responsibilities]]: same principles, framework-specific homes. The running example is a real refactor of a dev-only error-notification feature, where a maintainer's review pushed each piece into its correct layer.

## TL;DR

- Order layers by **how much each depends on**. Push logic **down** to the layer that depends least, because that layer is the most portable and testable.
- **Dependencies point one direction.** Lower never imports upper, and never a cycle. A cycle gives a pure layer a second reason to change.
- **Smart vs dumb is about data access**, not size or tree position. A smart component injects a service; a dumb one only takes inputs.
- **Two kinds of parsing.** Wire-to-domain lives once at the data-access boundary; domain-to-display lives in the presentation layer.
- **Interceptors and guards detect and delegate.** They never compute view-models.

## The placement axis: how much a piece depends on

The four pieces of the example feature are not just different topics, they form a gradient by *how much each depends on*:

```
  interceptor / feature component   TOP: depends on the framework, state, the app
  stateful service                  depends on held state
  presentational component          depends only on its @Input
  parseErrorBody(data)              BOTTOM: depends on nothing, portable
```

`parseErrorBody` imports nothing from Angular, so you could copy it into a plain Node script and it works. The interceptor is pinned into Angular's HTTP pipeline and goes nowhere. That difference is the axis.

"Depends on" here is not a head-count. By raw import count a smart component often references more than a two-line interceptor, since it injects several services, holds state, wires a template, and coordinates children. The axis measures two other things. First, how **welded to the framework** a piece is, meaning whether it can run or be tested outside Angular at all. Second, how **cross-cutting its scope** is, meaning one screen versus every request in the app. An interceptor sits at the top on scope. It runs over the whole HTTP pipeline, so its reasons to change come from app-wide request conventions like a new correlation-id header or a global retry policy, not from one feature. The load-bearing parts of the gradient are its two ends, a pure function at the bottom that depends on nothing and framework plumbing at the top, together with the rule to push logic down. The exact rank of neighbours in the fuzzy middle, interceptor versus smart component, drives no decision.

The placement rule follows. **Push logic down to the layer that depends on the least it can get away with.** The bottom layer has the least coupling to the framework, so it is the cheapest to change, the easiest to reuse, and the fastest to test (no `TestBed`, no providers). The canonical Angular style-guide instruction, "keep components presentation-focused, refactor complex logic out into pure functions or services," is this rule applied.

## Dependency direction is one-way

Higher layers import lower ones. Lower layers never import upward, and two layers never import each other.

The reason is a reasons-to-change argument (see [[software-design/splitting-responsibilities]]). A pure function is valuable precisely because nothing forces it to change. The day it `import`s from a component above it, a restructure of that component now forces an edit to the pure function too. It has gained a **second reason to change**, which is an SRP violation, and it has lost the portability and isolated testability that justified its existence. A cycle poisons the very thing the bottom layer was for.

This is not etiquette. In Nx the four library types (`feature`, `ui`, `data-access`, `util`) carry a strictly one-directional allowed-import list, and `@nx/enforce-module-boundaries` fails the build when a `ui` or `util` layer imports from a `feature`. The machine guards the arrow so humans cannot quietly reverse it.

## Smart vs dumb is about data access, not tree position

A **smart** (container) component reaches out for its data. It injects a service, holds state, handles user intent. A **dumb** (presentational) component receives everything through `@Input` and reports back through outputs, and injects nothing.

The common trap is to key this on size or tree depth ("top-level is smart, nested is dumb"). The example refactor runs the other way. `ErrorDetailsComponent` is the *large* one (renders error rows, statuses, sources, trace groups) yet it is dumb, because it only takes an `[error]` input. `ErrorNotificationsComponent` is *smaller* yet smart, because it injects the notification service. Size and depth are red herrings. The discriminator is how the component obtains what it needs, and it maps straight onto the depends-on axis. Smart depends on more (top), dumb depends only on its inputs (bottom). The tell that you drew the line right is that the dumb component's spec needs no providers.

> [Note] Practitioners debate whether smart components may sit deep in the tree (to avoid prop-drilling through many dumb layers). Keying the split on data-source access rather than tree position resolves it. A component that injects a service is smart wherever it sits.

## Where the two kinds of parsing live

"Parsing" hides two different jobs with different homes.

- **Wire-to-domain.** Turning an untrusted backend response into the app's own model. It depends on the *backend format* (volatile, outside your control) and many parts of the app consume the result. So it lives **once, at the data-access boundary** (a service), which isolates that volatility. The day the backend or the framework HTTP type changes, one place changes instead of every consumer.
- **Domain-to-display.** Turning an app value into what a view shows, like a date into `"3 days ago"`. It depends on the *design*, not the backend, and is usually needed by one view. So it lives in the **presentation layer**, a component `computed()` if local, or a shared pipe if many views need it. It never belongs back at the data boundary.

The example feature blurred these. The service stored the raw `HttpErrorResponse` and both the container and the child re-derived display rows from it (the double-parse). That was a deliberate trade. Storing the raw framework type keeps derivation local to each view (**locality of behaviour**), but it means every derive site depends on Angular's HTTP types, so a change to `HttpRequest.urlWithParams` is felt in several components. The **isolation** alternative parses once at the boundary into an app-owned model, so only the boundary feels such a change, at the cost of a layer of indirection. Both are defensible. The point is to make the call on purpose and note it in the review.

## Interceptors and guards detect and delegate

Interceptors and route guards are cross-cutting plumbing at the very top of the stack. Their job is limited to **detect and delegate**. Catch the request or navigation, decide whether it applies, and hand off. A functional interceptor is literally `(req, next) => next(req)`, so the shape *is* delegation.

Because they depend on the whole pipeline, they must not compute or build view-models. The example's original interceptor parsed the response body and reshaped the request into display structures. That is the smell. The fix pushed the parsing down into a pure function and cut the interceptor to `errorNotifications.notify(error, request)`. If you catch an interceptor, guard, or resolver building a view-model, the logic wants to move down into a service or a pure function.

## Deciding where new code goes

Ask, in order, and stop at the first yes:

1. Does it touch the framework at all? No, then it is a **pure function / model file** (`util`). Most logic can be pushed here, and it is the cheapest to test, so bias toward it.
2. Is it transforming one already-parsed value for display? Then a **presentational component** or a **pipe**.
3. Does it hold state, fetch data, or turn wire data into the domain model? Then a **service** (`data-access`).
4. Does it coordinate services, state, or user intent for a screen? Then a **smart / container component** (`feature`).
5. Is it cross-cutting across many requests or routes? Then an **interceptor / guard** (detect and delegate only).
6. Would it work unchanged in another app? Then **shared / ui**. Is it app-wide plumbing? Then **core**. Is it a user-facing flow? Then a **feature**.

The smells that say a boundary is wrong:

- A component spec needs a large pile of providers. The component is too smart; push rendering into a dumb child.
- A service exposes formatted strings or many `derivedX$` streams. Derivation leaked upward; move it into components.
- An interceptor, guard, or resolver builds a view-model. Compute leaked into plumbing; move it down.
- The same transformation runs in two places. The logic wants to live once (the double-parse hint).
- A `shared` or `util` module imports from a `feature`. It is misfiled, or the arrow is reversed.
- You cannot describe a unit's job in one sentence without "and". It has two responsibilities.

## Tradeoffs and gotchas

- **Do not pre-split.** The gradient is the target shape, not a mandate. A 30-line feature can be one component and one service. Apply the split when a file starts doing two jobs or a spec starts fighting you, not before. (consensus)
- **Locality vs isolation is unsettled.** Keeping derivation next to the view (locality) versus parsing once at the boundary (isolation) is a real trade with no universal winner. Decide per feature and by how volatile the wire format is. (consensus on the trade, contested on the default)
- **The facade debate.** Whether to wrap state (NgRx or signals) behind a facade service is genuinely contested. Critics call it indirection that cancels itself out; proponents treat misuse as a discipline problem. Do not present a facade as mandatory. (contested)
- **Standalone-era drift.** The old `CoreModule` / `SharedModule` singleton guidance is superseded by `providedIn: 'root'` and route-level environment injectors. Class-based guards, resolvers, and `HttpInterceptor` still compile but the functional forms are idiomatic since v14/15. Deprecation is not removal. (single-voice, version-specific)

## Related Concepts

- [[software-design/splitting-responsibilities]]: the framework-free principles (SRP by actor, connascence, cohesion) that this page applies to Angular.
- [[software-design/judging-abstractions]]: a wrong abstraction is often several concerns merged behind flags, which is the same failure seen from the abstraction side.

## References

- [Nx project dependency rules](https://nx.dev/docs/concepts/decisions/project-dependency-rules): the four library types and the one-directional dependency hierarchy.
- [Angular style guide](https://angular.dev/style-guide): organize by feature, keep components presentation-focused, refactor logic out.
- [Angular dependency injection](https://angular.dev/guide/di): services, `providedIn: 'root'`, injection contexts.
- [Angular HTTP interceptors](https://angular.dev/guide/http/interceptors): the functional `(req, next)` signature and `next()` delegation.

**Practitioner / opinion:**

- [Angular architecture best practices](https://dev-academy.com/angular-architecture-best-practices/): a layered presentation / facade / core guide with the smart-dumb split.
- [Smart, UI and sandbox facades](https://blog.simplified.courses/smart-components-ui-components-and-sandbox-facades-in-angular/): relaxing smart/dumb purity in deep trees.
