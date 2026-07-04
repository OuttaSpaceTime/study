---
wiki: software-design/splitting-responsibilities
section: Command-Query Separation and CQS vs CQRS
kind: predict-output
env: python312
questions:
- Which CQS property does can_retry break, and why does that make it unsafe to drop into a log line or debugger watch?
- Name a sanctioned exception where a method deliberately mutates and returns, and what separates it from this case.
created: 2026-07-03
---

## Brief

can_retry looks like a harmless query, so a developer calls it once for a check, once in a log line, and once more for the real decision. Predict all three printed lines.

## Stub

```python
class Session:
    def __init__(self):
        self.attempts_left = 3

    def can_retry(self):
        self.attempts_left -= 1
        return self.attempts_left > 0

s = Session()
print("check:", s.can_retry())
print("log line:", s.can_retry())
print("decision:", s.can_retry())
```

## Solution

```python
class Session:
    def __init__(self):
        self.attempts_left = 3

    def can_retry(self):
        self.attempts_left -= 1
        return self.attempts_left > 0

s = Session()
print("check:", s.can_retry())
print("log line:", s.can_retry())
print("decision:", s.can_retry())
```

## Expected Output

```
check: True
log line: True
decision: False
```
