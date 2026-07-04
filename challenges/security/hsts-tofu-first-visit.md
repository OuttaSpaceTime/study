---
wiki: security/hsts
section: TOFU Problem (Trust On First Use)
kind: predict-output
env: python312
questions:
- Why is the very first visit still vulnerable even when the site serves HSTS correctly?
- Which mechanism closes this first-visit gap entirely?
created: 2026-07-04
---

## Brief

A tiny browser model prints the scheme of the first network request for each visit. The store gains the host once a visit completes over HTTPS. Predict both lines.

## Stub

```python
hsts_store = set()

def first_hop(host):
    scheme = "https" if host in hsts_store else "http"
    hsts_store.add(host)
    return f"{scheme}://{host}"

print(first_hop("bank.example"))
print(first_hop("bank.example"))
```

## Solution

```python
hsts_store = set()

def first_hop(host):
    scheme = "https" if host in hsts_store else "http"
    hsts_store.add(host)
    return f"{scheme}://{host}"

print(first_hop("bank.example"))
print(first_hop("bank.example"))
```

## Expected Output

```
http://bank.example
https://bank.example
```
