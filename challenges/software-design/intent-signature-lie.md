---
wiki: software-design/reading-code-for-intent
section: The signature is a contract
kind: predict-output
env: ts-node24
questions:
- Whose bug is the crash, the caller's or getUser's, and why?
- What is the honest signature, and what does it force every caller to do?
created: 2026-07-04
---

## Brief

The signature promises a User on every return, and the caller trusts it. User "2" does not exist. Predict both console lines.

## Stub

```ts
type User = { id: string; email: string };

const users: Record<string, User> = {
  "1": { id: "1", email: "ada@example.com" },
};

function getUser(id: string): User {
  return users[id];
}

try {
  console.log(getUser("1").email);
  console.log(getUser("2").email);
} catch (e) {
  console.log("crash:", (e as Error).message);
}
```

## Solution

```ts
type User = { id: string; email: string };

const users: Record<string, User> = {
  "1": { id: "1", email: "ada@example.com" },
};

function getUser(id: string): User {
  return users[id];
}

try {
  console.log(getUser("1").email);
  console.log(getUser("2").email);
} catch (e) {
  console.log("crash:", (e as Error).message);
}
```

## Expected Output

```
ada@example.com
crash: Cannot read properties of undefined (reading 'email')
```
