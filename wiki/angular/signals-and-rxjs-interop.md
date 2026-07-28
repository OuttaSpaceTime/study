---
title: Signals and RxJS Interop
aliases:
- toSignal
- signals rxjs interop
- signals vs async pipe
tags:
- angular
- frontend
- signals
- rxjs
created: '2026-05-07'
updated: '2026-06-25'
source_skill: study-walkthrough
last_deepened: '2026-05-07'
next_review: '2026-07-30'
review_interval: 30
flashcard_ids: []
---


# Signals and RxJS Interop

Signals are Angular's reactivity primitive; RxJS observables model async workflows. They are complementary, and `toSignal()` is the bridge that lets observables drive rendering through the signal path.

## Signals push-pull model vs Zone.js passive patching

A signal pushes invalidation. Calling `.set()` notifies all registered consumers that the value changed. Consumers pull the current value when they read it. The model is push-pull. The consumer is told when to re-read and pulls the value on demand.

Zone.js is passive. It patches async APIs and fires CD after every task, whether or not anything changed. The browser owns the trigger cadence.

With signals, your code owns the trigger. `signal.set(x)` is the trigger. No Zone patching required.

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

- [[angular/signals-and-change-detection]]: how a signal write turns into a re-render via semi-local CD, the traversal flag, and why it only pays off in zoneless mode
- [[angular/change-detection]]: Zone.js mechanics, Default vs OnPush strategies, the four dirty triggers

## References

- [Angular: Signals overview](https://angular.dev/guide/signals): covers signal primitives, computed, effects, and their role in reactivity and CD
- [Angular: toSignal() API](https://angular.dev/api/core/rxjs-interop/toSignal): reference for the observable-to-signal bridge (stable as of v20)
