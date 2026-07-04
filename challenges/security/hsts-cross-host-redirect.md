---
wiki: security/hsts
section: Cross-Host Redirects
kind: predict-output
env: python312
questions:
- After the broken chain, which URL stays vulnerable on every future visit, not just the first?
- What does the extra same-host hop in the fixed chain accomplish?
created: 2026-07-04
---

## Brief

Every HTTPS response in this model serves an HSTS header, so a host enters the store only if the redirect chain touches it over HTTPS. Predict which hosts each chain protects.

## Stub

```python
hsts_store = set()

def follow(redirect_chain):
    for url in redirect_chain:
        scheme, host = url.split("://")
        if scheme == "https":
            hsts_store.add(host)

follow(["http://example.com", "https://www.example.com"])
print("broken chain protects:", sorted(hsts_store))

hsts_store.clear()
follow(["http://example.com", "https://example.com", "https://www.example.com"])
print("fixed chain protects: ", sorted(hsts_store))
```

## Solution

```python
hsts_store = set()

def follow(redirect_chain):
    for url in redirect_chain:
        scheme, host = url.split("://")
        if scheme == "https":
            hsts_store.add(host)

follow(["http://example.com", "https://www.example.com"])
print("broken chain protects:", sorted(hsts_store))

hsts_store.clear()
follow(["http://example.com", "https://example.com", "https://www.example.com"])
print("fixed chain protects: ", sorted(hsts_store))
```

## Expected Output

```
broken chain protects: ['www.example.com']
fixed chain protects:  ['example.com', 'www.example.com']
```
