---
wiki: security/same-origin-policy
section: What an Origin Is
kind: write-code
env: node24
questions:
- Which three URL components make up an origin, and what happens if just one differs?
- Are https://app.example.com and https://api.example.com the same origin, and why?
created: 2026-07-03
---

## Brief

An origin is the tuple of scheme, host, and port. Complete the comparison so the function matches the browser's same-origin check for the four classic cases.

## Stub

```js
const sameOrigin = (a, b) => {
  const ua = new URL(a), ub = new URL(b);
  return false; // TODO: compare the three URL parts that define an origin
};

console.log(`path differs:   ${sameOrigin("https://app.example.com", "https://app.example.com/api")}`);
console.log(`scheme differs: ${sameOrigin("https://app.example.com", "http://app.example.com")}`);
console.log(`host differs:   ${sameOrigin("https://app.example.com", "https://api.example.com")}`);
console.log(`port differs:   ${sameOrigin("https://app.example.com", "https://app.example.com:8080")}`);
```

## Solution

```js
const sameOrigin = (a, b) => {
  const ua = new URL(a), ub = new URL(b);
  return ua.protocol === ub.protocol && ua.hostname === ub.hostname && ua.port === ub.port;
};

console.log(`path differs:   ${sameOrigin("https://app.example.com", "https://app.example.com/api")}`);
console.log(`scheme differs: ${sameOrigin("https://app.example.com", "http://app.example.com")}`);
console.log(`host differs:   ${sameOrigin("https://app.example.com", "https://api.example.com")}`);
console.log(`port differs:   ${sameOrigin("https://app.example.com", "https://app.example.com:8080")}`);
```

## Expected Output

```
path differs:   true
scheme differs: false
host differs:   false
port differs:   false
```
