---
wiki: reactive/observable-error-handling
section: "Dead subscriber trap: subscribing after a subject has errored"
kind: write-code
env: node24
questions:
- What does a late subscriber to an errored subject receive, and when?
- Which subject variants or upstream patterns let late subscribers recover instead of hitting the stored error?
created: 2026-07-03
---

## Brief

A subject that has errored is in a terminal state. Fill in subscribe so late subscribers get exactly what RxJS gives them, which is the stored error immediately and nothing else ever.

## Stub

```js
class Subject {
  observers = [];
  closed = false;
  thrownError = null;

  subscribe(observer) {
    // TODO: handle a subject that has already errored before registering the observer
    this.observers.push(observer);
  }

  next(v) {
    if (!this.closed) this.observers.forEach((o) => o.next(v));
  }

  error(e) {
    if (this.closed) return;
    this.closed = true;
    this.thrownError = e;
    this.observers.forEach((o) => o.error(e));
  }
}

const subject = new Subject();
subject.subscribe({
  next: (v) => console.log('early next:', v),
  error: (e) => console.log('early error:', e.message),
});
subject.next('a');
subject.error(new Error('boom'));

subject.subscribe({
  next: (v) => console.log('late next:', v),
  error: (e) => console.log('late error:', e.message),
});
subject.next('b');
```

## Solution

```js
class Subject {
  observers = [];
  closed = false;
  thrownError = null;

  subscribe(observer) {
    if (this.closed) return observer.error(this.thrownError);
    this.observers.push(observer);
  }

  next(v) {
    if (!this.closed) this.observers.forEach((o) => o.next(v));
  }

  error(e) {
    if (this.closed) return;
    this.closed = true;
    this.thrownError = e;
    this.observers.forEach((o) => o.error(e));
  }
}

const subject = new Subject();
subject.subscribe({
  next: (v) => console.log('early next:', v),
  error: (e) => console.log('early error:', e.message),
});
subject.next('a');
subject.error(new Error('boom'));

subject.subscribe({
  next: (v) => console.log('late next:', v),
  error: (e) => console.log('late error:', e.message),
});
subject.next('b');
```

## Expected Output

```
early next: a
early error: boom
late error: boom
```
