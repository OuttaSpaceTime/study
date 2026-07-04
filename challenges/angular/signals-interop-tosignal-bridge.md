---
wiki: angular/signals-and-rxjs-interop
section: "toSignal(): observable-to-signal bridge and what it buys"
kind: write-code
env: node24
questions:
- Who subscribes to the observable when a template uses toSignal, and how many times?
- What does the template read before the first emission arrives, and which option fills that gap?
created: 2026-07-03
---

## Brief

toSignal() subscribes to the observable internally and mirrors every emission into a signal, so the template reads the signal and never touches the observable. Implement the bridge so reads return initialValue before the first emission and the latest emission afterward.

## Stub

```js
function createSignal(initial) {
  let value = initial;
  return { read: () => value, set: (next) => { value = next; } };
}

const users$ = {
  handlers: [],
  subscribe(next) { this.handlers.push(next); },
  next(v) { this.handlers.forEach((h) => h(v)); },
};

function toSignal(observable, { initialValue }) {
  // TODO: seed a signal with initialValue, subscribe once so every emission lands in the signal, return its read function
}

const users = toSignal(users$, { initialValue: "loading" });
console.log(users());
users$.next("alice");
console.log(users());
users$.next("bob");
console.log(users());
```

## Solution

```js
function createSignal(initial) {
  let value = initial;
  return { read: () => value, set: (next) => { value = next; } };
}

const users$ = {
  handlers: [],
  subscribe(next) { this.handlers.push(next); },
  next(v) { this.handlers.forEach((h) => h(v)); },
};

function toSignal(observable, { initialValue }) {
  const state = createSignal(initialValue);
  observable.subscribe((v) => state.set(v));
  return state.read;
}

const users = toSignal(users$, { initialValue: "loading" });
console.log(users());
users$.next("alice");
console.log(users());
users$.next("bob");
console.log(users());
```

## Expected Output

```
loading
alice
bob
```
