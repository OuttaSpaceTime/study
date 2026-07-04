---
wiki: angular/signals-and-change-detection
section: "Semi-local CD: which nodes are traversed vs which re-evaluate bindings"
kind: predict-output
env: ts-node24
questions:
- Why is Sidebar pruned instead of being traversed like List?
- What would each spine view print if the value had arrived through the async pipe instead of a signal?
created: 2026-07-03
---

## Brief

A signal read in Item changed, so markAncestorsForTraversal already stamped the flags shown below. Predict what the CD walk prints for each of the four views.

## Stub

```ts
const children: Record<string, string[]> = { App: ["Sidebar", "List"], Sidebar: [], List: ["Item"], Item: [] };
const flag: Record<string, string> = { App: "HasChildViewsToRefresh", Sidebar: "", List: "HasChildViewsToRefresh", Item: "RefreshView" };

function detectChanges(view: string) {
  if (flag[view] === "RefreshView") console.log(`${view}: re-evaluate bindings`);
  else if (flag[view] === "HasChildViewsToRefresh") console.log(`${view}: traversed, bindings untouched`);
  else {
    console.log(`${view}: pruned`);
    return;
  }
  for (const child of children[view]) detectChanges(child);
}

detectChanges("App");
```

## Solution

```ts
const children: Record<string, string[]> = { App: ["Sidebar", "List"], Sidebar: [], List: ["Item"], Item: [] };
const flag: Record<string, string> = { App: "HasChildViewsToRefresh", Sidebar: "", List: "HasChildViewsToRefresh", Item: "RefreshView" };

function detectChanges(view: string) {
  if (flag[view] === "RefreshView") console.log(`${view}: re-evaluate bindings`);
  else if (flag[view] === "HasChildViewsToRefresh") console.log(`${view}: traversed, bindings untouched`);
  else {
    console.log(`${view}: pruned`);
    return;
  }
  for (const child of children[view]) detectChanges(child);
}

detectChanges("App");
```

## Expected Output

```
App: traversed, bindings untouched
Sidebar: pruned
List: traversed, bindings untouched
Item: re-evaluate bindings
```
