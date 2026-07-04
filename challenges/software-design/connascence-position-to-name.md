---
wiki: software-design/splitting-responsibilities
section: Connascence as a coupling vocabulary
kind: write-code
env: python312
questions:
- Which connascence form does the new signature convert position into, and why does that count as strength reduction?
- What does strength measure in the connascence taxonomy?
created: 2026-07-03
---

## Brief

Callers of schedule must currently agree with it on argument order, which is connascence of position. Change the signature so the three numeric arguments can only be passed by name, making a swapped positional call fail loudly instead of silently misconfiguring the job.

## Stub

```python
def schedule(job, delay, priority, retries):  # TODO: make delay, priority, retries keyword-only
    print(job, "delay:", delay, "priority:", priority, "retries:", retries)

schedule("backup", delay=10, priority=3, retries=2)
try:
    schedule("backup", 10, 3, 2)
except TypeError:
    print("positional call rejected")
```

## Solution

```python
def schedule(job, *, delay, priority, retries):
    print(job, "delay:", delay, "priority:", priority, "retries:", retries)

schedule("backup", delay=10, priority=3, retries=2)
try:
    schedule("backup", 10, 3, 2)
except TypeError:
    print("positional call rejected")
```

## Expected Output

```
backup delay: 10 priority: 3 retries: 2
positional call rejected
```
