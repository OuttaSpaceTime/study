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
updated: '2026-05-07'
source_skill: study-walkthrough
depth: 1
last_deepened: '2026-05-07'
next_review: '2026-05-10'
review_interval: 3
probe_sections:
- Signals push-pull model vs Zone.js passive patching
- 'How signal writes mark ancestors: traversal flag vs dirty flag'
- 'Semi-local CD: which nodes are traversed vs which re-evaluate bindings'
- 'The click-event caveat: when semi-local CD collapses'
- 'toSignal(): observable-to-signal bridge and what it buys'
- 'Signals vs async pipe: when to use which'
last_probed:
- Signals push-pull model vs Zone.js passive patching
- 'How signal writes mark ancestors: traversal flag vs dirty flag'
- 'Semi-local CD: which nodes are traversed vs which re-evaluate bindings'
- 'The click-event caveat: when semi-local CD collapses'
- 'toSignal(): observable-to-signal bridge and what it buys'
- 'Signals vs async pipe: when to use which'
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

## The click-event caveat: when semi-local CD collapses

If the signal mutation originates from a template event handler (a click, an input event), Angular calls both `markAncestorsForTraversal` and `markViewDirty`. Both flags fire. The path is fully dirty. Every ancestor re-evaluates its bindings.

The semi-local benefit only holds when the signal mutation comes from outside a template event. Sources like a service, a timer, or a WebSocket callback qualify.

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
