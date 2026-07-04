---
wiki: reactive/observable-error-handling
section: Error in inner vs outer observable (flatMap/switchMap)
kind: predict-output
env: node24
questions:
- Why does C never appear in the uncaught run?
- Where must catchError sit to keep the outer stream alive when one inner request fails?
created: 2026-07-03
---

## Brief

Both runs flatten the same three values through an inner observable that errors on the second one. Predict the output of the uncaught run versus the run that catches inside the mapping function.

## Stub

```js
const inner = (v) => (observer) => {
  if (v === 'bad') return observer.error(new Error('inner boom'));
  observer.next(v.toUpperCase());
};

function mergeMapRun(label, project) {
  let closed = false;
  const downstream = {
    next: (v) => { if (!closed) console.log(label, 'next:', v); },
    error: (e) => { if (!closed) { closed = true; console.log(label, 'dead:', e.message); } },
  };
  for (const v of ['a', 'bad', 'c']) {
    if (closed) break;
    project(v)(downstream);
  }
}

mergeMapRun('uncaught', inner);
mergeMapRun('caught  ', (v) => (observer) => inner(v)({
  next: observer.next,
  error: (e) => observer.next('fallback for ' + v),
}));
```

## Solution

```js
const inner = (v) => (observer) => {
  if (v === 'bad') return observer.error(new Error('inner boom'));
  observer.next(v.toUpperCase());
};

function mergeMapRun(label, project) {
  let closed = false;
  const downstream = {
    next: (v) => { if (!closed) console.log(label, 'next:', v); },
    error: (e) => { if (!closed) { closed = true; console.log(label, 'dead:', e.message); } },
  };
  for (const v of ['a', 'bad', 'c']) {
    if (closed) break;
    project(v)(downstream);
  }
}

mergeMapRun('uncaught', inner);
mergeMapRun('caught  ', (v) => (observer) => inner(v)({
  next: observer.next,
  error: (e) => observer.next('fallback for ' + v),
}));
```

## Expected Output

```
uncaught next: A
uncaught dead: inner boom
caught   next: A
caught   next: fallback for bad
caught   next: C
```
