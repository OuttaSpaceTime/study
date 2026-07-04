---
wiki: angular/component-lifecycle
section: "ngOnChanges: fires on first render and batches all input changes"
kind: predict-output
env: node24
questions:
- On first render, when does ngOnChanges fire relative to the constructor and ngOnInit, and which components never see it?
- How does SimpleChange.firstChange distinguish the initial binding from a later update?
created: 2026-07-03
---

## Brief

The parent sets three inputs in one tick, then one input in a later tick. Each change detection run flushes all pending input changes into a single ngOnChanges call. Predict how many calls happen and with which keys.

## Stub

```js
let pending = {};

function setInput(name, value) {
  pending[name] = { currentValue: value };
}

function runChangeDetection(component) {
  if (Object.keys(pending).length) component.ngOnChanges(pending);
  pending = {};
}

let calls = 0;
const component = {
  ngOnChanges(changes) {
    calls += 1;
    console.log(`call ${calls}: ${Object.keys(changes).join(', ')}`);
  },
};

setInput('user', 'Ada');
setInput('theme', 'dark');
setInput('locale', 'de');
runChangeDetection(component);

setInput('user', 'Bob');
runChangeDetection(component);
```

## Solution

```js
let pending = {};

function setInput(name, value) {
  pending[name] = { currentValue: value };
}

function runChangeDetection(component) {
  if (Object.keys(pending).length) component.ngOnChanges(pending);
  pending = {};
}

let calls = 0;
const component = {
  ngOnChanges(changes) {
    calls += 1;
    console.log(`call ${calls}: ${Object.keys(changes).join(', ')}`);
  },
};

setInput('user', 'Ada');
setInput('theme', 'dark');
setInput('locale', 'de');
runChangeDetection(component);

setInput('user', 'Bob');
runChangeDetection(component);
```

## Expected Output

```
call 1: user, theme, locale
call 2: user
```
