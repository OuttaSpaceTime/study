---
wiki: security/hsts
section: "The HSTS header fields: max-age, includeSubDomains, preload"
kind: write-code
env: python312
questions:
- Why do browsers ignore a Strict-Transport-Security header that arrives over plain HTTP?
- What unit is max-age in, and what duration is recommended?
created: 2026-07-04
---

## Brief

Build the full Strict-Transport-Security header value for a two year policy that also covers subdomains and opts into the preload list.

## Stub

```python
two_years = 2 * 365 * 24 * 60 * 60
value = ...  # TODO: the header value with all three directives
print(f"Strict-Transport-Security: {value}")
```

## Solution

```python
two_years = 2 * 365 * 24 * 60 * 60
value = f"max-age={two_years}; includeSubDomains; preload"
print(f"Strict-Transport-Security: {value}")
```

## Expected Output

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```
