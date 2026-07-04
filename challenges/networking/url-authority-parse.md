---
wiki: networking/url-anatomy
section: URL anatomy at a glance
kind: predict-output
env: python312
questions:
- Which two delimiters bound the authority chunk in a URL?
- What can netloc contain that hostname never does?
created: 2026-07-03
---

## Brief

urlsplit maps the anatomy diagram onto a real parser. Predict all five lines, especially what lands in netloc versus hostname.

## Stub

```python
from urllib.parse import urlsplit

u = urlsplit("https://alice@www.example.com:8080/pixel?utm=foo#top")
print("netloc:  ", u.netloc)
print("hostname:", u.hostname)
print("path:    ", u.path)
print("query:   ", u.query)
print("fragment:", u.fragment)
```

## Solution

```python
from urllib.parse import urlsplit

u = urlsplit("https://alice@www.example.com:8080/pixel?utm=foo#top")
print("netloc:  ", u.netloc)
print("hostname:", u.hostname)
print("path:    ", u.path)
print("query:   ", u.query)
print("fragment:", u.fragment)
```

## Expected Output

```
netloc:   alice@www.example.com:8080
hostname: www.example.com
path:     /pixel
query:    utm=foo
fragment: top
```
