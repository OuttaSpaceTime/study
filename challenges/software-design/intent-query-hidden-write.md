---
wiki: software-design/reading-code-for-intent
section: The name is part of the contract
kind: predict-output
env: node24
questions:
- What would a competent caller reading the name hasPermission assume happens on each call, and which principle does the hidden write violate?
- Why is the harmless-looking debug line the most dangerous call here?
created: 2026-07-04
---

## Brief

hasPermission returns an honest boolean and every test passes. Predict all three lines, especially the audit row count.

## Stub

```js
const auditLog = [];

const user = {
  role: "editor",
  hasPermission(action) {
    auditLog.push(`${action} checked`);
    return this.role === "editor";
  },
};

if (user.hasPermission("edit")) {
  console.log("edit allowed");
}
console.log(`debug: ${user.hasPermission("edit")}`);
console.log(`audit rows written: ${auditLog.length}`);
```

## Solution

```js
const auditLog = [];

const user = {
  role: "editor",
  hasPermission(action) {
    auditLog.push(`${action} checked`);
    return this.role === "editor";
  },
};

if (user.hasPermission("edit")) {
  console.log("edit allowed");
}
console.log(`debug: ${user.hasPermission("edit")}`);
console.log(`audit rows written: ${auditLog.length}`);
```

## Expected Output

```
edit allowed
debug: true
audit rows written: 2
```
