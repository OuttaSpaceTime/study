---
wiki: reactive/observable-error-handling
section: "catchError: signature, recovery pattern, and re-throw"
kind: write-code
env: node24
questions:
- What must the function passed to catchError return, and what happens to the stream afterwards?
- How do you log an error inside catchError but still let it propagate downstream?
created: 2026-07-03
---

## Brief

Here an observable is just a function that takes an observer. Fill in the one line that makes catchError recover, so the stream continues from the replacement instead of dying.

## Stub

```js
const of = (...values) => (observer) => {
  values.forEach((v) => observer.next(v));
  observer.complete();
};

const failAfter = (value, message) => (observer) => {
  observer.next(value);
  observer.error(new Error(message));
};

const catchError = (selector) => (source) => (observer) => {
  source({
    next: (v) => observer.next(v),
    error: (e) => {
      // TODO: subscribe the same observer to the replacement observable the selector returns
    },
    complete: () => observer.complete(),
  });
};

catchError((err) => of('fallback for ' + err.message))(failAfter('first', 'boom'))({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});
```

## Solution

```js
const of = (...values) => (observer) => {
  values.forEach((v) => observer.next(v));
  observer.complete();
};

const failAfter = (value, message) => (observer) => {
  observer.next(value);
  observer.error(new Error(message));
};

const catchError = (selector) => (source) => (observer) => {
  source({
    next: (v) => observer.next(v),
    error: (e) => {
      selector(e)(observer);
    },
    complete: () => observer.complete(),
  });
};

catchError((err) => of('fallback for ' + err.message))(failAfter('first', 'boom'))({
  next: (v) => console.log('next:', v),
  error: (e) => console.log('error:', e.message),
  complete: () => console.log('complete'),
});
```

## Expected Output

```
next: first
next: fallback for boom
complete
```
