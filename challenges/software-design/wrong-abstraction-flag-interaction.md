---
wiki: software-design/judging-abstractions
section: The wrong-abstraction signal
kind: predict-output
env: python312
questions:
- Which two unrelated concerns interact to decide whether the unsubscribed user gets the message?
- Why did each flag look locally reasonable in the review where it was added?
created: 2026-07-03
---

## Brief

Two callers each bolted a flag onto a shared helper. Predict which of the two calls actually prints, given that the flags now interact inside the function.

## Stub

```python
def send_notification(user, message, urgent=False, skip_if_unsubscribed=True):
    if urgent:
        message = "[URGENT] " + message
    if skip_if_unsubscribed and user["unsubscribed"] and not urgent:
        return
    print("sent:", message)

alice = {"unsubscribed": True}
send_notification(alice, "weekly digest")
send_notification(alice, "password reset", urgent=True)
```

## Solution

```python
def send_notification(user, message, urgent=False, skip_if_unsubscribed=True):
    if urgent:
        message = "[URGENT] " + message
    if skip_if_unsubscribed and user["unsubscribed"] and not urgent:
        return
    print("sent:", message)

alice = {"unsubscribed": True}
send_notification(alice, "weekly digest")
send_notification(alice, "password reset", urgent=True)
```

## Expected Output

```
sent: [URGENT] password reset
```
