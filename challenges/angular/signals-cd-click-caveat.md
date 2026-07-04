---
wiki: angular/signals-and-change-detection
section: "The click-event caveat: two independent mechanisms"
kind: predict-output
env: ts-node24
questions:
- Why does App end up Dirty even though the signal write only asked for traversal through it?
- What still happens when a click handler runs but its body does nothing?
created: 2026-07-03
---

## Brief

A button with a click handler lives in Toolbar and its handler writes a signal that is read in Display. Angular fires two independent markings, wrapListener calls markViewDirty on the click host and the signal write calls markAncestorsForTraversal on the reader. Predict the final state each view reports, noting how the print resolves an overlap.

## Stub

```ts
const parent: Record<string, string | null> = { App: null, Toolbar: "App", Display: "App" };
const flags: Record<string, Set<string>> = { App: new Set(), Toolbar: new Set(), Display: new Set() };

function markViewDirty(view: string) {
  for (let v: string | null = view; v; v = parent[v]) flags[v].add("Dirty");
}

function markAncestorsForTraversal(view: string) {
  flags[view].add("RefreshView");
  for (let v = parent[view]; v; v = parent[v]) flags[v].add("HasChildViewsToRefresh");
}

markViewDirty("Toolbar");
markAncestorsForTraversal("Display");

for (const v of ["App", "Toolbar", "Display"]) {
  console.log(`${v}: ${flags[v].has("Dirty") ? "Dirty" : [...flags[v]].join(", ") || "-"}`);
}
```

## Solution

```ts
const parent: Record<string, string | null> = { App: null, Toolbar: "App", Display: "App" };
const flags: Record<string, Set<string>> = { App: new Set(), Toolbar: new Set(), Display: new Set() };

function markViewDirty(view: string) {
  for (let v: string | null = view; v; v = parent[v]) flags[v].add("Dirty");
}

function markAncestorsForTraversal(view: string) {
  flags[view].add("RefreshView");
  for (let v = parent[view]; v; v = parent[v]) flags[v].add("HasChildViewsToRefresh");
}

markViewDirty("Toolbar");
markAncestorsForTraversal("Display");

for (const v of ["App", "Toolbar", "Display"]) {
  console.log(`${v}: ${flags[v].has("Dirty") ? "Dirty" : [...flags[v]].join(", ") || "-"}`);
}
```

## Expected Output

```
App: Dirty
Toolbar: Dirty
Display: RefreshView
```
