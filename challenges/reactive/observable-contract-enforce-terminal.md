---
wiki: reactive/observables
section: "The Observable Contract: grammar and serial delivery rule"
kind: write-code
env: node24
questions:
- State the contract grammar and name the two terminal events it allows.
- Besides the grammar, what does the serial delivery rule forbid?
created: 2026-07-03
---

## Brief

This wrapper enforces the contract grammar onNext* (onError | onComplete)? against a misbehaving producer. Fill in the complete handler so no event ever follows a terminal event.

## Stub

```js
function enforceContract(observer) {
  let closed = false;
  return {
    next: (v) => { if (!closed) observer.next(v); },
    error: (e) => { if (!closed) { closed = true; observer.error(e); } },
    complete: () => {
      // TODO: forward complete only if no terminal event happened yet, then close
    },
  };
}

const s = enforceContract({
  next: (v) => console.log(`next ${v}`),
  error: (e) => console.log('error', e.message),
  complete: () => console.log('complete'),
});

s.next(1);
s.complete();
s.next(2);
s.complete();
s.error(new Error('too late'));
```

## Solution

```js
function enforceContract(observer) {
  let closed = false;
  return {
    next: (v) => { if (!closed) observer.next(v); },
    error: (e) => { if (!closed) { closed = true; observer.error(e); } },
    complete: () => {
      if (!closed) {
        closed = true;
        observer.complete();
      }
    },
  };
}

const s = enforceContract({
  next: (v) => console.log(`next ${v}`),
  error: (e) => console.log('error', e.message),
  complete: () => console.log('complete'),
});

s.next(1);
s.complete();
s.next(2);
s.complete();
s.error(new Error('too late'));
```

## Expected Output

```
next 1
complete
```
