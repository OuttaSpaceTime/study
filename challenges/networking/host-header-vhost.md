---
wiki: networking/url-anatomy
section: Host header and virtual hosts
kind: predict-output
env: node24
questions:
- Is the Host header found in the request or in the response?
- What do nginx server_name and Rails config.hosts compare against to pick a site?
created: 2026-07-03
---

## Brief

Two sites share one server on one IP, and the client connects by raw IP address. Predict what the site lookup prints.

## Stub

```js
import http from "node:http";

const sites = {
  "chat.example.com": "Chat app",
  "intranet.example.com": "Intranet wiki",
};

const server = http.createServer((req, res) => {
  res.end(sites[req.headers.host] ?? "unknown site");
});

server.listen(0, "127.0.0.1", () => {
  const { port } = server.address();
  const options = { host: "127.0.0.1", port, path: "/messages", headers: { Host: "chat.example.com" } };
  http.get(options, (res) => {
    res.on("data", (chunk) => console.log(chunk.toString()));
    res.on("end", () => server.close());
  });
});
```

## Solution

```js
import http from "node:http";

const sites = {
  "chat.example.com": "Chat app",
  "intranet.example.com": "Intranet wiki",
};

const server = http.createServer((req, res) => {
  res.end(sites[req.headers.host] ?? "unknown site");
});

server.listen(0, "127.0.0.1", () => {
  const { port } = server.address();
  const options = { host: "127.0.0.1", port, path: "/messages", headers: { Host: "chat.example.com" } };
  http.get(options, (res) => {
    res.on("data", (chunk) => console.log(chunk.toString()));
    res.on("end", () => server.close());
  });
});
```

## Expected Output

```
Chat app
```
