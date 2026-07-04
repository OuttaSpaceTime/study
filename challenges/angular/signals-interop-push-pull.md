---
wiki: angular/signals-and-rxjs-interop
section: Signals push-pull model vs Zone.js passive patching
kind: write-code
env: node24
questions:
- What exactly does a signal push to its consumers on set, and when does the value itself move?
- How does this differ from Zone.js, which schedules CD after every patched task even when nothing changed?
created: 2026-07-03
---

## Brief

A signal pushes invalidation and its consumers pull the current value on demand. Complete set() so it stores the new value and then notifies every consumer, without ever passing the value along.

## Stub

```js
function createSignal(initial) {
  let value = initial;
  const consumers = new Set();
  const read = () => value;
  const set = (next) => {
    // TODO: store the new value, then push invalidation to every consumer (notify only, never pass the value)
  };
  return { read, set, onInvalidate: (fn) => consumers.add(fn) };
}

const count = createSignal(0);
count.onInvalidate(() => console.log(`pushed: stale, pulled: ${count.read()}`));
count.set(1);
count.set(2);
```

## Solution

```js
function createSignal(initial) {
  let value = initial;
  const consumers = new Set();
  const read = () => value;
  const set = (next) => {
    value = next;
    consumers.forEach((notify) => notify());
  };
  return { read, set, onInvalidate: (fn) => consumers.add(fn) };
}

const count = createSignal(0);
count.onInvalidate(() => console.log(`pushed: stale, pulled: ${count.read()}`));
count.set(1);
count.set(2);
```

## Expected Output

```
pushed: stale, pulled: 1
pushed: stale, pulled: 2
```
