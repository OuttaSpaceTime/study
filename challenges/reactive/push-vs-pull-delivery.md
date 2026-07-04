---
wiki: reactive/reactive-programming
section: "Reactive programming definition: streams as first-class values"
kind: predict-output
questions:
- Who decides when data is delivered in the pull model versus the push model?
- Why does the push value log last even though subscribe runs before the final console.log?
env: node24
created: 2026-07-03
---

## Brief

In the pull model the consumer asks for data and gets it inline. In the push model the consumer hands over an observer and the producer delivers whenever it is ready. Predict the order of the three log lines.

## Stub

```js
const pull = () => 'data';
console.log('pull:', pull());

const stream = {
  subscribe(observer) {
    setTimeout(() => observer.next('data'), 0);
  },
};

stream.subscribe({ next: (v) => console.log('push:', v) });
console.log('subscribed, still waiting');
```

## Solution

```js
const pull = () => 'data';
console.log('pull:', pull());

const stream = {
  subscribe(observer) {
    setTimeout(() => observer.next('data'), 0);
  },
};

stream.subscribe({ next: (v) => console.log('push:', v) });
console.log('subscribed, still waiting');
```

## Expected Output

```
pull: data
subscribed, still waiting
push: data
```
