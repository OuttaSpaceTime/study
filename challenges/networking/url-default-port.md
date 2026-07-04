---
wiki: networking/url-anatomy
section: "Port: default ports and when the URL includes one"
kind: predict-output
env: node24
questions:
- Which port does the browser use for http://localhost, and why does a dev server on 3000 then refuse the connection?
- Why does http://example.com:443/ keep its port in the href while https://example.com:443/ loses it?
created: 2026-07-03
---

## Brief

Every URL has a port even when none is written. Predict the port property and the normalized href for each of the four URLs.

## Stub

```js
for (const s of [
  "https://example.com/",
  "https://example.com:443/",
  "http://example.com:443/",
  "http://localhost:3000/",
]) {
  const u = new URL(s);
  console.log(`${s} port=${JSON.stringify(u.port)} href=${u.href}`);
}
```

## Solution

```js
for (const s of [
  "https://example.com/",
  "https://example.com:443/",
  "http://example.com:443/",
  "http://localhost:3000/",
]) {
  const u = new URL(s);
  console.log(`${s} port=${JSON.stringify(u.port)} href=${u.href}`);
}
```

## Expected Output

```
https://example.com/ port="" href=https://example.com/
https://example.com:443/ port="" href=https://example.com/
http://example.com:443/ port="443" href=http://example.com:443/
http://localhost:3000/ port="3000" href=http://localhost:3000/
```
