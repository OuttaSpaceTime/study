---
wiki: networking/url-anatomy
section: Path and query
kind: write-code
env: node24
questions:
- Which URL component never reaches the server, and why can that mislead server-side analytics?
- Does url.search include the leading question mark?
created: 2026-07-03
---

## Brief

The browser turns a full URL into the request line's target. Build that target from the parsed URL, keeping exactly the components the server actually receives.

## Stub

```js
const url = new URL("https://shop.example.com/search?q=mug&page=2#reviews");

// TODO: build the request target exactly as the browser writes it after GET
const target = "";

console.log(`GET ${target} HTTP/1.1`);
```

## Solution

```js
const url = new URL("https://shop.example.com/search?q=mug&page=2#reviews");

const target = url.pathname + url.search;

console.log(`GET ${target} HTTP/1.1`);
```

## Expected Output

```
GET /search?q=mug&page=2 HTTP/1.1
```
