---
wiki: angular/change-detection
section: "Mutation on @Input: why the child's view goes stale"
kind: write-code
env: node24
questions:
- What exactly does Angular compare when deciding whether an @Input dirties an OnPush child?
- Why do the parent's own bindings still update after a mutation while the OnPush child's DOM goes stale?
created: 2026-07-03
---

## Brief

An OnPush child is only dirtied when its @Input receives a new reference under a strict equality check. Update the user's name in a way that opens the gate.

## Stub

```js
const inputGateOpens = (previouslyBound, next) => previouslyBound !== next;

let user = { name: 'Ada' };
const previouslyBound = user;

// TODO: change user's name to 'Bob' so the OnPush input gate opens
// (user.name = 'Bob' would keep the gate closed)

console.log('gate opens:', inputGateOpens(previouslyBound, user));
console.log('name:', user.name);
```

## Solution

```js
const inputGateOpens = (previouslyBound, next) => previouslyBound !== next;

let user = { name: 'Ada' };
const previouslyBound = user;

user = { ...user, name: 'Bob' };

console.log('gate opens:', inputGateOpens(previouslyBound, user));
console.log('name:', user.name);
```

## Expected Output

```
gate opens: true
name: Bob
```
