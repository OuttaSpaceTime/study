---
wiki: software-design/software-complexity
section: Essential versus accidental complexity, and why the split matters
kind: predict-output
env: python312
questions:
- Which of the two checks is essential and which is accidental, and what test decides that?
- What does the accidental check cost, and what protection does it buy in return?
created: 2026-07-04
---

## Brief

Two null-shaped checks, one at the boundary and one downstream. Trace what get_current_user guarantees before predicting which lines can actually print.

## Stub

```python
def get_current_user(session):
    if session.get("user") is None:
        raise PermissionError("not signed in")
    return session["user"]

def handle_request(session):
    user = get_current_user(session)
    if user is None:
        print("guard fired: no user")
        return
    print("serving", user)

handle_request({"user": "ada"})
try:
    handle_request({})
except PermissionError as e:
    print("boundary raised:", e)
```

## Solution

```python
def get_current_user(session):
    if session.get("user") is None:
        raise PermissionError("not signed in")
    return session["user"]

def handle_request(session):
    user = get_current_user(session)
    if user is None:
        print("guard fired: no user")
        return
    print("serving", user)

handle_request({"user": "ada"})
try:
    handle_request({})
except PermissionError as e:
    print("boundary raised:", e)
```

## Expected Output

```
serving ada
boundary raised: not signed in
```
