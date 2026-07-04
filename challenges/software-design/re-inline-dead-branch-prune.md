---
wiki: software-design/judging-abstractions
section: The remedy is re-inline, then re-derive
kind: write-code
env: python312
questions:
- Why does the pruned caller body reveal the real seam better than refactoring the shared function forward?
- Which branches died for this caller, and what does each dead branch tell you about the other callers?
created: 2026-07-03
---

## Brief

You decided send_notification is the wrong abstraction. Inline it into this one caller and delete every branch the caller can never hit, so its true behavior becomes visible.

## Stub

```python
def send_notification(user, message, sms=False, urgent=False,
                      skip_if_unsubscribed=True):
    if urgent:
        message = "[URGENT] " + message
    if skip_if_unsubscribed and user["unsubscribed"] and not urgent:
        return
    if sms:
        print("sms:", message)
    else:
        print("email:", message)

def notify_password_reset(user):
    # TODO: inline the call below, then delete every branch
    # this caller can never hit
    send_notification(user, "password reset", urgent=True)

notify_password_reset({"unsubscribed": True})
```

## Solution

```python
def notify_password_reset(user):
    message = "[URGENT] password reset"
    print("email:", message)

notify_password_reset({"unsubscribed": True})
```

## Expected Output

```
email: [URGENT] password reset
```
