---
title: Signals and Change Detection
aliases:
- angular signals CD
- angular signals change detection
- toSignal
- semi-local change detection
- zoneless angular
tags:
- angular
- frontend
- change-detection
- signals
- rxjs
created: '2026-05-07'
updated: '2026-05-30'
source_skill: study-walkthrough
last_deepened: '2026-05-07'
next_review: '2026-06-22'
review_interval: 12
probe_sections:
- Signals push-pull model vs Zone.js passive patching
- 'How signal writes mark ancestors: traversal flag vs dirty flag'
- 'Semi-local CD: which nodes are traversed vs which re-evaluate bindings'
- Why change detection walks top-down
- 'The click-event caveat: two independent mechanisms'
- When the caveat bites vs when semi-local CD survives
- Why semi-local CD only matters in zoneless
- 'toSignal(): observable-to-signal bridge and what it buys'
- 'Signals vs async pipe: when to use which'
last_probed:
- 'The click-event caveat: two independent mechanisms'
- When the caveat bites vs when semi-local CD survives
- Why semi-local CD only matters in zoneless
- Why change detection walks top-down
- 'toSignal(): observable-to-signal bridge and what it buys'
- 'Signals vs async pipe: when to use which'
- Signals push-pull model vs Zone.js passive patching
- 'How signal writes mark ancestors: traversal flag vs dirty flag'
- 'Semi-local CD: which nodes are traversed vs which re-evaluate bindings'
flashcard_ids: []
---


# Signals and Change Detection

Signals give Angular a data-driven CD trigger. Instead of Zone.js watching the browser for any async task, signal writes notify Angular exactly which components need updating.

## Signals push-pull model vs Zone.js passive patching

A signal pushes invalidation. Calling `.set()` notifies all registered consumers that the value changed. Consumers pull the current value when they read it. The model is push-pull. The consumer is told when to re-read and pulls the value on demand.

Zone.js is passive. It patches async APIs and fires CD after every task, whether or not anything changed. The browser owns the trigger cadence.

With signals, your code owns the trigger. `signal.set(x)` is the trigger. No Zone patching required.

## How signal writes mark ancestors: traversal flag vs dirty flag

When a component's template reads a signal, the component registers as a reactive consumer of that signal.

When the signal's value changes:

- OnPush's dirty marking (`markViewDirty`) stamps the component and all ancestors as dirty. Every ancestor reruns its own bindings during the next CD cycle.
- Signal's marking (`markAncestorsForTraversal`) stamps ancestors with `HasChildViewsToRefresh`. This is a traversal-only flag.

During the CD walk, `HasChildViewsToRefresh` tells Angular to traverse into that subtree to find the flagged leaf. Angular does not re-check the ancestor's own bindings.

## Semi-local CD: which nodes are traversed vs which re-evaluate bindings

Only the signal-consuming leaf component fully re-evaluates its template bindings. Ancestors between root and the leaf are traversed but not re-checked.

This is semi-local CD. One component re-evaluates its bindings; many ancestors are merely walked.

The `async` pipe differs. It calls `markForCheck()`, which uses the full dirty path. Every ancestor from root to the leaf re-evaluates its own bindings on each emission.

## Why change detection walks top-down

The reactive graph knows the exact set of views that consume a changed signal, so why not refresh those leaves directly? Because *knowing* the dirty leaf and *refreshing* it are separate machines. The refresh is executed by a CD pass that recursively walks the component view tree from the root down. There is no path to teleport into an arbitrary view and refresh it in isolation.

The ancestor flag is the routing breadcrumb for that walk. At each node the walker checks `HasChildViewsToRefresh`. Marked spine means descend; an unmarked subtree is pruned and skipped. Without the flags the walk could only find the leaf by visiting everything, which is the global CD signals exist to avoid.

The walk is top-down for correctness, not just convenience:

- **Data flows down.** A parent's bindings feed child `@Input()`s, so parents must update before children (the same invariant behind `ExpressionChangedAfterChecked`). A leaf refreshed in isolation could read stale inputs.
- **Structural dependence.** A child's existence can depend on its parent (`@if`, `@for`), so the parent's structural state must settle first.

The three flags involved are distinct. `HasChildViewsToRefresh` (ancestors) is pure routing with no binding check. `RefreshView` (the consuming leaf) means re-run this view's bindings. `Dirty` (set by `markViewDirty`) is the separate OnPush path. `markAncestorsForTraversal` always terminates at a leaf flagged `RefreshView` (traversal with no refresh target would be pointless), but the ancestors it marks are never re-checked. That asymmetry is the whole saving.

So the signal graph supplies *targeting* (which leaves, and the spine to reach them); the top-down walk supplies *ordering*. Traversing the spine is a cheap per-node flag check. Re-running binding expressions, the expensive part, still happens only at the flagged leaf.

## The click-event caveat: two independent mechanisms

When a signal is mutated from inside a template event handler (`<button (click)="count.set(...)">`), two *independent* mechanisms fire, and conflating them hides what actually happens:

1. **The click listener** (not the signal). Angular's `wrapListener` calls `markViewDirty` on the component that *hosts the `(click)` binding*, after the handler runs, regardless of what the handler does. An empty `(click)="noop()"` still does this. It walks up to root stamping `Dirty`. This predates signals. It's why OnPush components have always re-rendered on their own click handlers.
2. **The signal write** `count.set(...)`. This calls `markAncestorsForTraversal` on the signal's consumers, landing wherever `count` is *read*, exactly as for any other signal mutation.

The determinant is split two ways. `markViewDirty` is driven by **where the `(click)` binding lives** (dirties up to root); traversal is driven by **where the signal is read**. Both markings poke the CD scheduler, which **coalesces them into a single tick**; where they overlap on the same view, `Dirty` wins (recompute beats traverse-through).

## When the caveat bites vs when semi-local CD survives

The caveat only bites when the signal is read **at or above** the button's host: the click's dirty-walk already runs up to root, so any consumer on that upward path recomputes as a side effect of the click, not because the signal asked for it. The signal's careful leaf-targeting is wasted there.

If the signal is read in the *same* component as the button, that component is `Dirty` from mechanism 1 and recomputes regardless. The traversal flag is redundant.

Semi-local CD survives in full only when the signal mutation comes from **outside** a template event (a service, a timer, a WebSocket callback), where mechanism 1 never fires and only `markAncestorsForTraversal` runs.

## Why semi-local CD only matters in zoneless

The signal markings (`markAncestorsForTraversal`) run identically whether or not Zone.js is loaded. The *benefit*, though, only materializes in **zoneless** mode.

With Zone.js present, Zone fires a global CD pass after every async task regardless of what changed. The targeted leaf-only traversal is drowned out by zone's blanket top-down sweeps, so you pay full CD anyway. Remove the zone (`provideZonelessChangeDetection`) and the signal write becomes the *only* trigger, so the minimal traversal is what actually executes. The optimization is invisible with a zone and load-bearing without one.

The click caveat is itself a zoneless artifact. Without a zone, nothing automatically schedules CD when a user clicks. Angular's event-listener wrapper does the scheduling instead, by calling `markViewDirty` on the host component, the explicit replacement for zone's old automatic CD-on-events. So mechanism 1 from the caveat above *is* the zoneless event-handling path. The full dirty walk on a click is the price of not having a zone to do it implicitly.

## toSignal(): observable-to-signal bridge and what it buys

`toSignal()` wraps an observable in a signal at the component boundary:

```ts
// class
users$ = this.service.getUsers();   // Observable stays as-is
users  = toSignal(this.users$);     // signal at the template boundary

// template
@for (u of users(); track u.id) { ... }
```

`toSignal()` subscribes internally. The template reads the signal, not the observable. Each emission updates the signal, which triggers semi-local CD on this component only. The full dirty path is not involved.

This keeps RxJS for async workflows and gives signals the rendering boundary.

## Signals vs async pipe: when to use which

| | `async` pipe | `toSignal()` |
|---|---|---|
| CD trigger path | `markForCheck()` (full dirty path) | `markAncestorsForTraversal` (leaf only) |
| Ancestor cost per emission | Full binding re-evaluation on all ancestors | Traversal only |
| Template syntax | `{{ stream$ \| async }}` | `{{ stream() }}` |
| Best for | Low-frequency streams, simple setup | High-frequency streams, deep trees, zoneless |

Signals and RxJS are complementary. Use signals for state (component fields, derived values with `computed()`). Use observables for async workflows (HTTP, WebSocket, form events). Bridge them with `toSignal()`.

## Related Concepts

- [[angular/change-detection]]: Zone.js mechanics, Default vs OnPush strategies, the four dirty triggers

## References

- [Angular: Signals overview](https://angular.dev/guide/signals): covers signal primitives, computed, effects, and their role in reactivity and CD
- [Angular: toSignal() API](https://angular.dev/api/core/rxjs-interop/toSignal): reference for the observable-to-signal bridge (stable as of v20)
- [Angular: Zoneless guide](https://angular.dev/guide/zoneless): explains `provideZonelessChangeDetection`, the semi-local CD model, and migration path
