---
wiki: reactive/observables
section: "Subscription lifecycle: what subscribe returns and how teardown works"
kind: write-code
env: node24
questions:
- How does a producer register teardown logic, and when does it run?
- Why is a missed unsubscribe on a long-lived observable a memory leak?
created: 2026-07-03
---

## Brief

The producer returns a cleanup function that clears its interval. Complete subscribe so it returns a Subscription whose unsubscribe runs that teardown and stops the ticks.

## Stub

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) {
    const teardown = this.producer({ next });
    // TODO: return a Subscription object whose unsubscribe() runs the teardown
  }
}

const ticks$ = new Obs(subscriber => {
  let n = 0;
  const id = setInterval(() => subscriber.next(n++), 200);
  return () => { clearInterval(id); console.log('teardown ran'); };
});

const sub = ticks$.subscribe(v => console.log(`tick ${v}`));
setTimeout(() => sub.unsubscribe(), 700);
```

## Solution

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) {
    const teardown = this.producer({ next });
    return { unsubscribe: () => teardown() };
  }
}

const ticks$ = new Obs(subscriber => {
  let n = 0;
  const id = setInterval(() => subscriber.next(n++), 200);
  return () => { clearInterval(id); console.log('teardown ran'); };
});

const sub = ticks$.subscribe(v => console.log(`tick ${v}`));
setTimeout(() => sub.unsubscribe(), 700);
```

## Expected Output

```
tick 0
tick 1
tick 2
teardown ran
```
