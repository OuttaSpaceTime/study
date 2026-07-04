---
wiki: reactive/reactive-programming
section: "Stream anatomy: values, errors, and completion over time"
kind: predict-output
env: node24
questions:
- Which of the three event types are terminal, and can one stream ever emit both?
- What does a marble diagram with neither a pipe nor an X mean for the complete handler?
created: 2026-07-03
---

## Brief

This mini player turns a marble diagram string into observer callbacks. Predict which handler fires for each character of the two diagrams from the page.

## Stub

```js
function play(marble, observer) {
  for (const ch of marble) {
    if (ch === '|') return observer.complete();
    if (ch === 'X') return observer.error(new Error('boom'));
    if (ch !== '-') observer.next(ch);
  }
}

const observerFor = (label) => ({
  next: (v) => console.log(label, 'next:', v),
  error: (e) => console.log(label, 'error:', e.message),
  complete: () => console.log(label, 'complete'),
});

play('--a--b--c--|', observerFor('s1'));
play('--a--b--X--', observerFor('s2'));
```

## Solution

```js
function play(marble, observer) {
  for (const ch of marble) {
    if (ch === '|') return observer.complete();
    if (ch === 'X') return observer.error(new Error('boom'));
    if (ch !== '-') observer.next(ch);
  }
}

const observerFor = (label) => ({
  next: (v) => console.log(label, 'next:', v),
  error: (e) => console.log(label, 'error:', e.message),
  complete: () => console.log(label, 'complete'),
});

play('--a--b--c--|', observerFor('s1'));
play('--a--b--X--', observerFor('s2'));
```

## Expected Output

```
s1 next: a
s1 next: b
s1 next: c
s1 complete
s2 next: a
s2 next: b
s2 error: boom
```
