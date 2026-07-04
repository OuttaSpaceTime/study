---
wiki: angular/change-detection
section: "Zone.js: what triggers CD and what it cannot know"
kind: write-code
env: node24
questions:
- Why does a CD cycle get scheduled after the no-op callback even though no data changed?
- Which browser APIs does Zone.js patch, and at what moment does it notify Angular?
created: 2026-07-03
---

## Brief

Zone.js works by monkey-patching async APIs and notifying Angular after every task, whether or not anything changed. Complete the patched setTimeout so a CD cycle is scheduled right after each callback finishes.

## Stub

```js
let cycles = 0;
const scheduleCD = () => console.log(`CD cycle ${++cycles} scheduled`);

const originalSetTimeout = globalThis.setTimeout;
globalThis.setTimeout = (callback, delay) => {
  // TODO: run the task via originalSetTimeout, then notify Angular once the callback finishes
};

let count = 0;
setTimeout(() => { count++; }, 0);
setTimeout(() => {}, 0);
```

## Solution

```js
let cycles = 0;
const scheduleCD = () => console.log(`CD cycle ${++cycles} scheduled`);

const originalSetTimeout = globalThis.setTimeout;
globalThis.setTimeout = (callback, delay) => {
  originalSetTimeout(() => { callback(); scheduleCD(); }, delay);
};

let count = 0;
setTimeout(() => { count++; }, 0);
setTimeout(() => {}, 0);
```

## Expected Output

```
CD cycle 1 scheduled
CD cycle 2 scheduled
```
