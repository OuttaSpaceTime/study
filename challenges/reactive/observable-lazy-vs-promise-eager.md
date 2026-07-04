---
wiki: reactive/observables
section: Why observables are lazy and what subscribe triggers
kind: predict-output
env: node24
questions:
- What triggers the producer function inside an Observable to run?
- How does a Promise executor differ from an Observable producer at construction time?
created: 2026-07-03
---

## Brief

An Observable producer and a Promise executor are constructed side by side, but only one of them is consumed. Predict the order of the log lines.

## Stub

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) { this.producer({ next }); }
}

const obs$ = new Obs(subscriber => {
  console.log('observable producer runs');
  subscriber.next('obs value');
});

const promise = new Promise(resolve => {
  console.log('promise executor runs');
  resolve('promise value');
});

console.log('--- neither consumed yet ---');
obs$.subscribe(v => console.log('got', v));
```

## Solution

```js
class Obs {
  constructor(producer) { this.producer = producer; }
  subscribe(next) { this.producer({ next }); }
}

const obs$ = new Obs(subscriber => {
  console.log('observable producer runs');
  subscriber.next('obs value');
});

const promise = new Promise(resolve => {
  console.log('promise executor runs');
  resolve('promise value');
});

console.log('--- neither consumed yet ---');
obs$.subscribe(v => console.log('got', v));
```

## Expected Output

```
promise executor runs
--- neither consumed yet ---
observable producer runs
got obs value
```
