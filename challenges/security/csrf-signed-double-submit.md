---
wiki: security/csrf
section: Synchronizer token vs. signed double-submit cookie
kind: write-code
env: python312
questions:
- Why does the naive double-submit cookie break when an attacker controls a sibling subdomain?
- What does binding the token with HMAC(session + random, serverSecret) buy you that a plain random value does not?
created: 2026-07-04
---

## Brief

The naive double-submit cookie only checks that the cookie value equals the body value, so an attacker who can write a cookie and copy it into the body passes the check. The fix signs the token with an HMAC keyed by a server secret. Without the secret the attacker cannot produce a matching signature even when they know the session id and random value.

## Stub

```python
import hmac
import hashlib

SERVER_SECRET = b"server-secret-key"

def make_token(session_id, random_value):
    # TODO: sign session_id + random_value with SERVER_SECRET using HMAC-SHA256, return hexdigest
    ...

def valid(session_id, random_value, token):
    return hmac.compare_digest(make_token(session_id, random_value), token)

sid, rnd = "sess-abc", "r123"
legit = make_token(sid, rnd)
print("legit:", valid(sid, rnd, legit))

attacker_secret = b"guessed-secret"
forged = hmac.new(attacker_secret, (sid + rnd).encode(), hashlib.sha256).hexdigest()
print("forged:", valid(sid, rnd, forged))
```

## Solution

```python
import hmac
import hashlib

SERVER_SECRET = b"server-secret-key"

def make_token(session_id, random_value):
    return hmac.new(SERVER_SECRET, (session_id + random_value).encode(), hashlib.sha256).hexdigest()

def valid(session_id, random_value, token):
    return hmac.compare_digest(make_token(session_id, random_value), token)

sid, rnd = "sess-abc", "r123"
legit = make_token(sid, rnd)
print("legit:", valid(sid, rnd, legit))

attacker_secret = b"guessed-secret"
forged = hmac.new(attacker_secret, (sid + rnd).encode(), hashlib.sha256).hexdigest()
print("forged:", valid(sid, rnd, forged))
```

## Expected Output

```
legit: True
forged: False
```
