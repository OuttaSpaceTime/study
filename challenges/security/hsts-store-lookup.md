---
wiki: security/hsts
section: Browser Storage
kind: write-code
env: python312
questions:
- At what point in a navigation does the browser consult this store, relative to DNS and TCP?
- What does receiving max-age=0 over HTTPS do to a store entry?
created: 2026-07-04
---

## Brief

Before any packet leaves the machine, the browser upgrades a host if the store holds the host itself or any parent domain flagged includeSubDomains. Complete the matching rule.

## Stub

```python
store = {
    "example.com": {"include_subdomains": True},
    "app.other.com": {"include_subdomains": False},
}

def upgraded(host):
    labels = host.split(".")
    for i in range(len(labels)):
        candidate = ".".join(labels[i:])
        entry = store.get(candidate)
        # TODO: return True when this entry covers host
    return False

for host in ["example.com", "api.example.com", "app.other.com", "deep.app.other.com"]:
    print(host, upgraded(host))
```

## Solution

```python
store = {
    "example.com": {"include_subdomains": True},
    "app.other.com": {"include_subdomains": False},
}

def upgraded(host):
    labels = host.split(".")
    for i in range(len(labels)):
        candidate = ".".join(labels[i:])
        entry = store.get(candidate)
        if entry and (candidate == host or entry["include_subdomains"]):
            return True
    return False

for host in ["example.com", "api.example.com", "app.other.com", "deep.app.other.com"]:
    print(host, upgraded(host))
```

## Expected Output

```
example.com True
api.example.com True
app.other.com True
deep.app.other.com False
```
