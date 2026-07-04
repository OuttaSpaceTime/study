---
wiki: reactive/reactive-programming
section: "flatMap/mergeMap: collapsing a stream of streams"
kind: predict-output
env: node24
questions:
- What is the metastream in this snippet, and which call collapses it?
- In RxJS, what happens to the inner observables if you use map without a flattening operator?
created: 2026-07-03
---

## Brief

Arrays are the synchronous analog of streams, and request maps each click to a whole new stream of responses. Predict the shape map produces versus flatMap.

## Stub

```js
const clicks = ['click1', 'click2'];
const request = (click) => [`${click}:respA`, `${click}:respB`];

console.log('map:     ' + JSON.stringify(clicks.map(request)));
console.log('flatMap: ' + JSON.stringify(clicks.flatMap(request)));
```

## Solution

```js
const clicks = ['click1', 'click2'];
const request = (click) => [`${click}:respA`, `${click}:respB`];

console.log('map:     ' + JSON.stringify(clicks.map(request)));
console.log('flatMap: ' + JSON.stringify(clicks.flatMap(request)));
```

## Expected Output

```
map:     [["click1:respA","click1:respB"],["click2:respA","click2:respB"]]
flatMap: ["click1:respA","click1:respB","click2:respA","click2:respB"]
```
