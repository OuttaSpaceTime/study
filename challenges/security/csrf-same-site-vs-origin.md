---
wiki: security/csrf
section: Why SameSite=Lax doesn't fully protect against subdomain attacks
kind: predict-output
env: python312
questions:
- Why does SameSite still send the cookie from evil.example.com to app.example.com?
- What is the scope of SameSite (registrable domain) versus the scope of the Same-Origin Policy (full origin)?
created: 2026-07-04
---

## Brief

SameSite is scoped to the registrable domain (eTLD+1), not the full origin. Two sibling subdomains share a registrable domain, so they are same-site even though they are not same-origin. That gap is why a compromised subdomain bypasses SameSite entirely.

## Stub

```python
def registrable_domain(host):
    return ".".join(host.split(".")[-2:])

def same_site(a, b):
    return registrable_domain(a) == registrable_domain(b)

def same_origin(a, b):
    return a == b

pairs = [
    ("app.example.com", "evil.example.com"),
    ("app.example.com", "app.example.com"),
    ("app.example.com", "app.other.com"),
]
for a, b in pairs:
    print(f"{a} vs {b}: same_site={same_site(a, b)} same_origin={same_origin(a, b)}")
```

## Solution

```python
def registrable_domain(host):
    return ".".join(host.split(".")[-2:])

def same_site(a, b):
    return registrable_domain(a) == registrable_domain(b)

def same_origin(a, b):
    return a == b

pairs = [
    ("app.example.com", "evil.example.com"),
    ("app.example.com", "app.example.com"),
    ("app.example.com", "app.other.com"),
]
for a, b in pairs:
    print(f"{a} vs {b}: same_site={same_site(a, b)} same_origin={same_origin(a, b)}")
```

## Expected Output

```
app.example.com vs evil.example.com: same_site=True same_origin=False
app.example.com vs app.example.com: same_site=True same_origin=True
app.example.com vs app.other.com: same_site=False same_origin=False
```
