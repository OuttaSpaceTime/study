---
wiki: reactive/observable-error-handling
section: "How error terminates a stream: subscription state after onError"
kind: write-code
env: node24
questions:
- After onError fires, what happens to the subscription and which callbacks can still run?
- Why does the complete handler never fire for a stream that errors?
created: 2026-07-03
---

## Brief

RxJS wraps every observer in a safe subscriber that enforces the contract. Fill in the error path so that once the stream dies, nothing else is ever delivered.

## Stub

```js
function safeSubscriber(observer) {
  let closed = false;
  return {
    next: (v) => { if (!closed) observer.next(v); },
    error: (e) => {
      // TODO: deliver the error exactly once and close the subscription for good
    },
    complete: () => { if (!closed) { closed = true; observer.complete(); } },
  };
}

const s = safeSubscriber({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});

s.next('a');
s.error(new Error('boom'));
s.next('b');
s.complete();
```

## Solution

```js
function safeSubscriber(observer) {
  let closed = false;
  return {
    next: (v) => { if (!closed) observer.next(v); },
    error: (e) => {
      if (closed) return;
      closed = true;
      observer.error(e);
    },
    complete: () => { if (!closed) { closed = true; observer.complete(); } },
  };
}

const s = safeSubscriber({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});

s.next('a');
s.error(new Error('boom'));
s.next('b');
s.complete();
```

## Expected Output

```
next: a
error: boom
```
