---
wiki: reactive/reactive-programming
section: "Core operator categories: transform, filter, combine, flatten"
kind: write-code
env: node24
questions:
- Why does scan work on an infinite stream where reduce would never emit anything?
- Which operator category does scan belong to, and what does it emit that reduce does not?
created: 2026-07-03
---

## Brief

scan is a running accumulator: like reduce, but it emits every intermediate value instead of only the final one. Fill in the loop body of this array analog of the operator.

## Stub

```js
function scan(values, fn, seed) {
  let acc = seed;
  const out = [];
  for (const v of values) {
    // TODO: update the accumulator and emit the intermediate value
  }
  return out;
}

console.log('scan:   ' + JSON.stringify(scan([1, 2, 3, 4], (acc, v) => acc + v, 0)));
console.log('reduce: ' + [1, 2, 3, 4].reduce((acc, v) => acc + v, 0));
```

## Solution

```js
function scan(values, fn, seed) {
  let acc = seed;
  const out = [];
  for (const v of values) {
    acc = fn(acc, v);
    out.push(acc);
  }
  return out;
}

console.log('scan:   ' + JSON.stringify(scan([1, 2, 3, 4], (acc, v) => acc + v, 0)));
console.log('reduce: ' + [1, 2, 3, 4].reduce((acc, v) => acc + v, 0));
```

## Expected Output

```
scan:   [1,3,6,10]
reduce: 10
```
