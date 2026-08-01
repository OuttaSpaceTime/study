---
title: Discriminated union narrowing
aliases:
- discriminated union narrowing
- literal discriminant
- control-flow narrowing
- nested discriminant
tags:
- typescript
- types
- narrowing
created: '2026-07-15'
updated: '2026-07-15'
source_skill: study-walkthrough
flashcard_ids: []
---

# Discriminated union narrowing

## TL;DR
- TypeScript narrows a union by control-flow analysis (CFA), but only when the union has a usable discriminant.
- A usable discriminant is a **top-level property whose type is a literal** (`type: 'a' | 'b'`). Declare it as `type: string` and narrowing silently stops working.
- CFA does not recurse. A nested discriminant like `item.attributes.kind` never narrows the parent `item`.
- To fix a nested case soundly, hoist the discriminant to the top level or narrow the inner object directly. A `x is T` guard also works but is an unchecked assertion.

## Control-flow Analysis and What It Narrows
CFA is how TypeScript refines a variable's type as it follows the code. Inside a branch guarded by `typeof`, `===`, `instanceof`, `in`, or a truthiness check, the variable is narrowed to what the check proves.

```ts
function f(x: string | number) {
  if (typeof x === 'string') {
    x // narrowed to string here
  }
}
```

CFA only ever concludes what it can prove from the checks in front of it. That single property explains every limitation below.

## A Discriminated Union Needs a Top-Level Literal Discriminant
A union is discriminated when its members share a property whose value is a distinct literal per member. The `===` check can then eliminate members.

```ts
type Entry =
  | { type: 'notif'; title: string }
  | { type: 'expiry'; email: string }

declare const e: Entry
if (e.type === 'notif') {
  e.title // e narrowed to the notif member
}
```

Widen that discriminant to `string` and it stops working. Both members now carry `type: string`, so `e.type === 'notif'` rules nothing out.

```ts
type Loose =
  | { type: string; title: string }
  | { type: string; email: string }
// e.type === 'notif' narrows nothing. No literal, no discriminant.
```

This is the trap behind a JSON:API generic that declares `type: string`. Parameterize the field to a literal and narrowing comes back. See [[openapi/schema-composition]] for the wire-schema side (`oneOf`).

Since TypeScript 5.5 an inline `arr.filter(e => e.type === 'notif')` narrows the result to the matching member on its own, because the callback gets an inferred type predicate. That only works once the union is genuinely discriminated. See [[typescript/type-guards-and-inferred-predicates]].

## Nested Discriminants Do not Narrow the Parent Union
Discriminant analysis looks only at the **direct** properties of the union members. It does not dig into nested objects, so a discriminant one level down never narrows the parent.

```ts
type Notif = { attributes: { itemType: 'ml_notification' }; rel: number }
type Memb = { attributes: { itemType: 'membership_expiry' }; rel: number }
type Plain = { attributes: { itemType: 'x' | 'y' } } // no rel
type Item = Notif | Memb | Plain

declare const item: Item
if (item.attributes.itemType === 'ml_notification') {
  item.rel // ERROR. Plain survived, item did not narrow.
}
```

This was verified by compiling under both `--strict` and non-strict. The nested check fails to narrow in both modes, so nesting itself is the blocker, not the compiler flags.

## Cleaner Fixes for a Nested Discriminant
Ranked from most to least sound.

1. **Hoist a top-level literal discriminant.** Give each member a direct literal property and narrow on that. It makes the object a real discriminated union with no assertion and no guard. Best when you own the type.
2. **Destructure and narrow the inner object.** `const { attributes } = item; if (attributes.itemType === 'x') { attributes.foo }`. TypeScript 4.4+ narrows the local `attributes`. It narrows the inner object, not `item`, so use it when the inner data is all you need.
3. **A `x is T` type guard.** Forces narrowing of the whole object, but it is an unchecked assertion. See [[typescript/type-guards-and-inferred-predicates]].

Two things do not work. Extracting the discriminant **value** to a local (`const k = item.attributes.itemType`) narrows `k`, never `item`. `satisfies` does nothing for narrowing, it is an assignability check only.

## strictNullChecks Does not Defeat a Clean Boolean Discriminant
A boolean literal (`deleted: false | true`) is a perfectly good discriminant, and a clean union narrows on it with or without `strictNullChecks`.

```ts
type B = { del: false; x: number } | { del: true }
function fromBool(e: B): number {
  return e.del === false ? e.x : 0 // narrows under strict AND non-strict
}
```

Verified by compiling under `--strict` and under `--strict --strictNullChecks false`. Both narrow. So the folk explanation that "`false` and `true` collapse to `boolean` when `strictNullChecks` is off" is wrong.

What `strictNullChecks` actually governs is `null` and `undefined`. With it off, `null` and `undefined` are absorbed into every type and nullish guards do nothing.

> [Note] In one real codebase a `deleted`-keyed union failed to narrow only under the app's non-strict config, and a `x is T` guard rescued it. The clean-union probes above show the boolean discriminant was not the cause. The precise structural trigger (the union arrived through a generic indexed-access plus intersection) was not fully isolated. If a boolean union will not narrow, suspect the surrounding type construction, not the boolean.

## Related Concepts
- [[typescript/type-guards-and-inferred-predicates]] - forcing and inferring narrowing with predicates
- [[openapi/schema-composition]] - `oneOf` discriminated unions on the wire
- [[sql/nullable-columns]] - modeling optional versus required at the data layer

## References
- [TS Handbook, Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) - CFA, discriminated unions, the literal-discriminant requirement
- [TS 4.4 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-4.html) - aliased conditions and discriminants (narrowing a destructured local)
- microsoft/TypeScript [#50651](https://github.com/microsoft/TypeScript/issues/50651) and [#18758](https://github.com/microsoft/TypeScript/issues/18758) - nested and child-to-parent discriminant narrowing (open or not planned)
