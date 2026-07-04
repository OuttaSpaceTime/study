---
wiki: angular/signals-and-change-detection
section: "How signal writes mark ancestors: traversal flag vs dirty flag"
kind: write-code
env: ts-node24
questions:
- Which flag does markAncestorsForTraversal put on ancestors, and why does the CD walk never re-check their bindings?
- How would the printed flags differ if markViewDirty had been called on Item instead?
created: 2026-07-03
---

## Brief

A signal read in the leaf view Item just changed. markViewDirty shows the OnPush marking pattern. Implement the signal marking, which flags the same path asymmetrically.

## Stub

```ts
const parent: Record<string, string | null> = { App: null, List: "App", Item: "List" };
const flags: Record<string, string[]> = { App: [], List: [], Item: [] };

function markViewDirty(view: string) {
  for (let v: string | null = view; v; v = parent[v]) flags[v].push("Dirty");
}

function markAncestorsForTraversal(view: string) {
  // TODO: flag the consuming view for a binding re-run, then flag each ancestor
  // with the traversal-only flag
}

markAncestorsForTraversal("Item");
for (const v of ["App", "List", "Item"]) console.log(`${v}: ${flags[v].join(", ") || "-"}`);
```

## Solution

```ts
const parent: Record<string, string | null> = { App: null, List: "App", Item: "List" };
const flags: Record<string, string[]> = { App: [], List: [], Item: [] };

function markViewDirty(view: string) {
  for (let v: string | null = view; v; v = parent[v]) flags[v].push("Dirty");
}

function markAncestorsForTraversal(view: string) {
  flags[view].push("RefreshView");
  for (let v = parent[view]; v; v = parent[v]) flags[v].push("HasChildViewsToRefresh");
}

markAncestorsForTraversal("Item");
for (const v of ["App", "List", "Item"]) console.log(`${v}: ${flags[v].join(", ") || "-"}`);
```

## Expected Output

```
App: HasChildViewsToRefresh
List: HasChildViewsToRefresh
Item: RefreshView
```
