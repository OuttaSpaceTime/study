---
wiki: security/same-origin-policy
section: Server-to-Server Requests
kind: predict-output
env: node24
questions:
- The response carries no Access-Control-Allow-Origin header. Why does the read still succeed here?
- What credentials does a server-side request carry compared to a browser request?
created: 2026-07-03
---

## Brief

A Node process fetches from a server that sends no CORS headers, while claiming to come from evil.com. Predict whether reading the body succeeds.

## Stub

```js
import http from "node:http";

const server = http.createServer((req, res) => res.end("balance: 42"));

server.listen(0, async () => {
  const res = await fetch(`http://127.0.0.1:${server.address().port}/`, {
    headers: { Origin: "https://evil.com" },
  });
  console.log(`allow-origin header: ${res.headers.get("access-control-allow-origin")}`);
  console.log(`body: ${await res.text()}`);
  server.close();
});
```

## Solution

```js
import http from "node:http";

const server = http.createServer((req, res) => res.end("balance: 42"));

server.listen(0, async () => {
  const res = await fetch(`http://127.0.0.1:${server.address().port}/`, {
    headers: { Origin: "https://evil.com" },
  });
  console.log(`allow-origin header: ${res.headers.get("access-control-allow-origin")}`);
  console.log(`body: ${await res.text()}`);
  server.close();
});
```

## Expected Output

```
allow-origin header: null
body: balance: 42
```
