---
wiki: angular/where-code-belongs
section: Where the two kinds of parsing live
kind: write-code
env: ts-node24
questions:
- Why does this parse live once at the data-access boundary instead of in each consuming component?
- Where would a formatter that turns occurredAt into "3 days ago" live, and why not here?
created: 2026-07-04
---

## Brief

The backend sends untrusted snake_case wire data. Write the one wire-to-domain parse at the data-access boundary so no consumer ever touches the wire format again.

## Stub

```ts
type AppError = { url: string; status: number; occurredAt: Date };

const wire = { request_url: "/api/users", status_code: 500, occurred_at: "2026-07-01T12:00:00Z" };

function parseErrorBody(data: any): AppError {
  // TODO: map the wire fields onto the app-owned model
}

const error = parseErrorBody(wire);
console.log(`${error.status} ${error.url} ${error.occurredAt.toISOString()}`);
```

## Solution

```ts
type AppError = { url: string; status: number; occurredAt: Date };

const wire = { request_url: "/api/users", status_code: 500, occurred_at: "2026-07-01T12:00:00Z" };

function parseErrorBody(data: any): AppError {
  return {
    url: data.request_url,
    status: data.status_code,
    occurredAt: new Date(data.occurred_at),
  };
}

const error = parseErrorBody(wire);
console.log(`${error.status} ${error.url} ${error.occurredAt.toISOString()}`);
```

## Expected Output

```
500 /api/users 2026-07-01T12:00:00.000Z
```
