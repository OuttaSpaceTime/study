---
wiki: reactive/observable-error-handling
section: "retry vs retryWhen: immediate resubscription vs conditional backoff"
kind: predict-output
env: node24
questions:
- Why does the producer function run three times here instead of once?
- What extra option does retry accept in RxJS 7 to add exponential backoff between attempts?
created: 2026-07-03
---

## Brief

This cold source fails twice, then succeeds. Predict how often the producer runs and what the downstream observer sees under retry(3).

## Stub

```js
let calls = 0;
const source = (observer) => {
  calls += 1;
  console.log('producer run ' + calls);
  if (calls < 3) return observer.error(new Error('fail ' + calls));
  observer.next('data');
  observer.complete();
};

const retry = (count) => (src) => (observer) => {
  let remaining = count;
  const attempt = () => src({
    next: (v) => observer.next(v),
    error: (e) => (remaining-- > 0 ? attempt() : observer.error(e)),
    complete: () => observer.complete(),
  });
  attempt();
};

retry(3)(source)({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});
```

## Solution

```js
let calls = 0;
const source = (observer) => {
  calls += 1;
  console.log('producer run ' + calls);
  if (calls < 3) return observer.error(new Error('fail ' + calls));
  observer.next('data');
  observer.complete();
};

const retry = (count) => (src) => (observer) => {
  let remaining = count;
  const attempt = () => src({
    next: (v) => observer.next(v),
    error: (e) => (remaining-- > 0 ? attempt() : observer.error(e)),
    complete: () => observer.complete(),
  });
  attempt();
};

retry(3)(source)({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});
```

## Expected Output

```
producer run 1
producer run 2
producer run 3
next: data
complete
```
