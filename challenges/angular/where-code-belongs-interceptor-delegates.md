---
wiki: angular/where-code-belongs
section: Interceptors and guards detect and delegate
kind: write-code
env: ts-node24
questions:
- What is the smell when an interceptor parses response bodies into display structures?
- After the fix, where did the parsing logic move and why there?
created: 2026-07-04
---

## Brief

An interceptor's whole job is detect and delegate. Complete the error interceptor so it hands errors off to notify and otherwise stays out of the request's way.

## Stub

```ts
const notify = (error: Error, req: string) => console.log(`notified: ${error.message} on ${req}`);

const handler = (req: string): string => {
  if (req.startsWith("/broken")) throw new Error("500");
  return `ok: ${req}`;
};

const errorInterceptor = (req: string, next: (req: string) => string): string => {
  // TODO: delegate to next; if it throws, notify(error, req) and rethrow
};

console.log(errorInterceptor("/api/users", handler));
try {
  errorInterceptor("/broken/route", handler);
} catch {
  console.log("error propagated");
}
```

## Solution

```ts
const notify = (error: Error, req: string) => console.log(`notified: ${error.message} on ${req}`);

const handler = (req: string): string => {
  if (req.startsWith("/broken")) throw new Error("500");
  return `ok: ${req}`;
};

const errorInterceptor = (req: string, next: (req: string) => string): string => {
  try {
    return next(req);
  } catch (error) {
    notify(error as Error, req);
    throw error;
  }
};

console.log(errorInterceptor("/api/users", handler));
try {
  errorInterceptor("/broken/route", handler);
} catch {
  console.log("error propagated");
}
```

## Expected Output

```
ok: /api/users
notified: 500 on /broken/route
error propagated
```
