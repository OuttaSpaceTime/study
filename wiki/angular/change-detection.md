---
title: Change Detection
aliases:
- angular CD
- OnPush change detection
- ChangeDetectionStrategy
- angular change detection strategy
tags:
- angular
- frontend
- change-detection
created: '2026-05-07'
updated: '2026-05-07'
source_skill: study-walkthrough
depth: 1
last_deepened: '2026-05-07'
next_review: '2026-07-17'
review_interval: 25
probe_sections:
- 'Zone.js: what triggers CD and what it cannot know'
- 'Default strategy: full DFS tree walk every cycle'
- 'OnPush: four conditions that dirty a component'
- 'Mutation on @Input: why the child''s view goes stale'
- setTimeout and manual subscribe silently miss OnPush
- markForCheck vs detectChanges
last_probed:
- 'Mutation on @Input: why the child''s view goes stale'
- setTimeout and manual subscribe silently miss OnPush
- markForCheck vs detectChanges
- 'Zone.js: what triggers CD and what it cannot know'
- 'Default strategy: full DFS tree walk every cycle'
- 'OnPush: four conditions that dirty a component'
flashcard_ids: []
---

# Change Detection

Angular's change detection determines which DOM nodes need updating. The mechanism has two distinct phases. The trigger phase decides when CD runs. The check phase decides what CD evaluates.

## Zone.js: what triggers CD and what it cannot know

Zone.js patches browser async APIs at startup. Patched APIs include `setTimeout`, `setInterval`, `addEventListener`, `Promise.then`, and XHR callbacks. When any patched task finishes, Zone notifies Angular to schedule a CD cycle.

Zone.js triggers CD unconditionally after every task, whether or not anything changed. It cannot know what your code did inside the task. Angular is reactive to browser events, not to data changes.

## Default strategy: full DFS tree walk every cycle

`ChangeDetectionStrategy.Default` (CheckAlways) visits every component in the tree on every CD cycle, depth-first top-to-bottom.

At each component, Angular re-evaluates every template binding expression and compares the result to the previously rendered value with `===`. A difference triggers a DOM patch.

Mutation works fine under Default. `this.user.name = 'Bob'` in a click handler updates the DOM because `user.name` evaluates to the new string value regardless of the object reference.

## OnPush: four conditions that dirty a component

`ChangeDetectionStrategy.OnPush` (CheckOnce) skips a component and its entire subtree unless the component is marked dirty. A component becomes dirty when any of four conditions are met:

1. An `@Input` binding receives a new reference (`===` against the previously passed value)
2. A DOM event fires from inside the component's own template (`(click)`, `(input)`, etc.)
3. An `async` pipe in the template emits a new value
4. `ChangeDetectorRef.markForCheck()` or `.detectChanges()` is called manually

When a component is marked dirty, Angular also marks every ancestor up to root dirty, so the tree walk can reach the dirty leaf.

## Mutation on @Input: why the child's view goes stale

The `@Input` dirty trigger checks `===` on the bound expression, not on individual properties. If a parent mutates a property on an object it passes down:

```ts
// parent — this.user reference unchanged
this.user.name = 'Bob';
```

The parent re-evaluates `[user]="user"`, gets the same reference, and the child's gate stays closed. The child is never dirtied. Its DOM shows the old value.

Replace the reference instead.

```ts
this.user = { ...this.user, name: 'Bob' };
```

The parent's own bindings still update under Default, because Default always re-evaluates template expressions directly. `{{ user.name }}` in the parent yields the new string, which differs from the rendered value. The `===` gate only applies to the child's `@Input` dirty-marking, not to how the parent evaluates its own bindings.

## setTimeout and manual subscribe silently miss OnPush

**setTimeout inside an OnPush component:**

```ts
ngOnInit() {
  setTimeout(() => this.count++, 1000);
}
```

Zone triggers CD when the callback fires. But `setTimeout` is not one of the four dirty triggers, so the component stays clean. CD skips it. DOM stale.

**Manual subscribe in ngOnInit:**

```ts
ngOnInit() {
  this.service.user$.subscribe(u => this.user = u);
}
```

The observable emits, the callback runs, `this.user` is reassigned. The assignment does not communicate with Angular. No dirty trigger fires. CD skips the component.

Both cases require routing the update through a dirty trigger. Call `cdr.markForCheck()` inside the callback, use the `async` pipe in the template, or use signals (see [[angular/signals-and-change-detection]]).

## markForCheck vs detectChanges

Both are methods on `ChangeDetectorRef`:

- `markForCheck()` marks the component and all ancestors dirty. CD checks this component on the next scheduled cycle.
- `detectChanges()` runs CD immediately on this component and its children, synchronously.

`markForCheck()` is the right default. Use `detectChanges()` for components detached from the CD tree or for explicit flush control in tests.

## Related Concepts

- [[angular/signals-and-change-detection]]: signals replace Zone.js as the CD trigger with semi-local, fine-grained updates

## References

- [Angular: Skipping component subtrees](https://angular.dev/best-practices/skipping-subtrees): official guide on OnPush strategy and when Angular skips subtrees during CD
- [Angular: Zone pollution](https://angular.dev/best-practices/zone-pollution): explains Zone.js mechanics and how to prevent unnecessary CD triggers
- [Angular: ChangeDetectorRef API](https://angular.dev/api/core/ChangeDetectorRef): reference for `markForCheck()`, `detectChanges()`, `detach()`, and related methods
