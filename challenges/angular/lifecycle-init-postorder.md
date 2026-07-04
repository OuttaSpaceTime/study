---
wiki: angular/component-lifecycle
section: "Init order: depth-first post-order across the tree"
kind: write-code
env: node24
questions:
- Why can a parent's ngAfterViewInit not run before its grandchild's?
- On a single component, which fires first, ngAfterContentInit or ngAfterViewInit?
created: 2026-07-03
---

## Brief

A view only counts as initialized once every descendant view is. Implement the traversal that fires ngAfterViewInit across the tree in the order Angular uses.

## Stub

```js
const children = { Parent: ['Child'], Child: ['Grandchild'], Grandchild: [] };

function runAfterViewInit(view) {
  // TODO: recurse and log `${view}: ngAfterViewInit` so descendants finish first
}

runAfterViewInit('Parent');
```

## Solution

```js
const children = { Parent: ['Child'], Child: ['Grandchild'], Grandchild: [] };

function runAfterViewInit(view) {
  for (const child of children[view]) runAfterViewInit(child);
  console.log(`${view}: ngAfterViewInit`);
}

runAfterViewInit('Parent');
```

## Expected Output

```
Grandchild: ngAfterViewInit
Child: ngAfterViewInit
Parent: ngAfterViewInit
```
