---
wiki: reactive/observables
section: "Cold vs hot observables: independent vs shared execution"
kind: predict-output
env: node24
questions:
- Why does each subscriber of a cold observable see a different run number here?
- Why is an HTTP request observable cold, and what operator makes subscribers share one request?
created: 2026-07-03
---

## Brief

The cold observable runs its producer once per subscriber, the hot one pushes a single shared event to everyone. Predict which values each subscriber receives.

## Stub

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) { this.producer({ next }); }
}

let run = 0;
const cold$ = new Obs(subscriber => {
  run += 1;
  subscriber.next(`run ${run}`);
});

cold$.subscribe(v => console.log('cold A:', v));
cold$.subscribe(v => console.log('cold B:', v));

const listeners = [];
const hot$ = new Obs(subscriber => listeners.push(subscriber));

hot$.subscribe(v => console.log('hot A:', v));
hot$.subscribe(v => console.log('hot B:', v));
listeners.forEach(s => s.next('shared event'));
```

## Solution

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) { this.producer({ next }); }
}

let run = 0;
const cold$ = new Obs(subscriber => {
  run += 1;
  subscriber.next(`run ${run}`);
});

cold$.subscribe(v => console.log('cold A:', v));
cold$.subscribe(v => console.log('cold B:', v));

const listeners = [];
const hot$ = new Obs(subscriber => listeners.push(subscriber));

hot$.subscribe(v => console.log('hot A:', v));
hot$.subscribe(v => console.log('hot B:', v));
listeners.forEach(s => s.next('shared event'));
```

## Expected Output

```
cold A: run 1
cold B: run 2
hot A: shared event
hot B: shared event
```
