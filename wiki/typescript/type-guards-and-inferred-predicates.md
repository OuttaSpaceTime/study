---
title: Type guards and inferred predicates
aliases:
- type guards
- inferred type predicates
- user-defined type guard
- filter Boolean trap
tags:
- typescript
- types
- narrowing
created: '2026-07-15'
updated: '2026-07-15'
source_skill: study-walkthrough
flashcard_ids: []
review_interval: 3
next_review: '2026-07-18'
---

# Type guards and inferred predicates

## TL;DR
- A user-defined type guard (`x is T`) is an assertion TypeScript trusts without checking. It can lie, and the compiler will not complain.
- Since TS 5.5 a simple predicate callback is inferred, so `arr.filter(e => e.type === 'x')` narrows the result with no explicit guard.
- Inference is all-or-nothing across four conditions. Break one and it silently falls back to `boolean`.
- `filter(Boolean)` does not get an inferred predicate. Use `x => x != null`.
- Checking `arr[0]` and asserting about the whole array is unsound. A `.every` check is sound and narrows the array on its own.

## User-defined type guards are unchecked assertions
A function returning `param is T` narrows its argument to `T` in the true branch. TypeScript takes the `is T` claim on faith and never verifies the body actually proves it.

```ts
function isNotif(item: Item): item is Notif {
  return item.attributes.itemType === 'ml_notification'
  // if this said 'membership_expiry' by mistake, TS would still trust it
}
```

That is the power and the danger. Guards force narrowing that control-flow analysis cannot derive, for example a nested discriminant (see [[typescript/discriminated-union-narrowing]]). In exchange you take on the correctness the compiler normally guarantees.

## Inferred type predicates and the four conditions
Since TypeScript 5.5 a function that returns a boolean is given an inferred type predicate when ALL of these hold.

1. No explicit return type or predicate annotation.
2. A single return statement, no implicit returns.
3. The parameter is not reassigned.
4. The returned expression is a boolean tied to a refinement of the parameter.

```ts
const isNum = (x: unknown) => typeof x === 'number' // inferred as `x is number`
```

Break any condition (add a second return, annotate `: boolean`, mutate the parameter) and inference silently reverts to `boolean` with no error. That fragility is why many teams still write guards explicitly.

## filter and every narrow, filter(Boolean) does not
An inferred predicate composes with array methods that carry a predicate overload.

```ts
type N = { type: 'n'; a: number }
type M = { type: 'm' }
declare const xs: (N | M)[]

xs.filter((e) => e.type === 'n') // N[], filter narrows the result
if (xs.every((e) => e.type === 'n')) {
  xs // N[], every narrows the receiver via its `this is S[]` overload
}
```

The famous trap is `filter(Boolean)`. `Boolean` is not itself a predicate, so the result stays `(T | null)[]`. Falsy-but-valid values (`0`, `''`, `false`) break the "false implies not-T" half of the predicate contract. Write `xs.filter((x) => x != null)` instead.

## Unsound shortcut versus sound check
A guard that inspects only `entries[0]` and asserts about the whole array is unsound. It promises homogeneity it never checked.

```ts
// UNSOUND: claims the whole array from element 0
function isAllN(es: (N | M)[]): es is N[] {
  return es.length === 0 || es[0].type === 'n'
}
```

TypeScript can never infer this promise, because it is false in general and inference only produces provable facts. The explicit `es is N[]` is load-bearing precisely because the body does not prove it. Such a guard is a deliberate vouch, often justified by an API contract that guarantees homogeneous arrays.

Make it sound with `.every` and the guard becomes unnecessary. An inline `if (es.every((e) => e.type === 'n'))` narrows `es` to `N[]` on its own (inferred predicate plus the `every` overload). The `arr[0]` version survives only as an O(1) shortcut that trades soundness for speed.

## Generic guards with Extract
When you need the same narrowing across several members, one generic guard beats N hand-written ones.

```ts
function isPresent<T extends { deleted: boolean }>(
  e: T,
): e is Extract<T, { deleted: false }> {
  return !e.deleted
}
```

`Extract<T, U>` selects the members of `T` assignable to `U`, so one guard narrows any `deleted`-keyed union to its present branch. It is still an unchecked assertion, just a DRY one.

## Related Concepts
- [[typescript/discriminated-union-narrowing]] - what CFA can narrow on its own, and its limits
- [[openapi/schema-composition]] - `oneOf` unions that these guards consume

## References
- [TS Handbook, Narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) - user-defined type guards
- [TS 5.5 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-5.html) - inferred type predicates and the four conditions
- **Practitioner / opinion:** [totaltypescript, type predicate inference](https://www.totaltypescript.com/type-predicate-inference) - filter(Boolean) still not inferred, guards are unchecked assertions
- **Practitioner / opinion:** [felt.com, narrowing with predicates and discriminated unions](https://felt.com/blog/narrowing-typescript-type-predicates-discriminated-unions) - prefer discriminated unions over guards for exhaustiveness
