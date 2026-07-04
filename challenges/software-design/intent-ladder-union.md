---
wiki: software-design/reading-code-for-intent
section: The ladder from documented to impossible
kind: write-code
env: ts-node24
questions:
- Which rung of the ladder does the union move the missing-user case to, and when is misuse now caught?
- Why is a thrown error on misuse weaker than this fix?
created: 2026-07-04
---

## Brief

getUser used to promise a User it could not always deliver. Climb to the top rung: complete the type so a caller who ignores the missing case cannot compile.

## Stub

```ts
type Found = { kind: "found"; email: string };
type Missing = { kind: "missing" };
// TODO: define Lookup so the compiler forces callers to handle both cases

function describe(result: Lookup): string {
  switch (result.kind) {
    case "found":
      return result.email;
    case "missing":
      return "no such user";
  }
}

console.log(describe({ kind: "found", email: "ada@example.com" }));
console.log(describe({ kind: "missing" }));
```

## Solution

```ts
type Found = { kind: "found"; email: string };
type Missing = { kind: "missing" };
type Lookup = Found | Missing;

function describe(result: Lookup): string {
  switch (result.kind) {
    case "found":
      return result.email;
    case "missing":
      return "no such user";
  }
}

console.log(describe({ kind: "found", email: "ada@example.com" }));
console.log(describe({ kind: "missing" }));
```

## Expected Output

```
ada@example.com
no such user
```
