---
wiki: software-design/reading-code-for-intent
section: Preconditions, postconditions, and asymmetric blame
kind: write-code
env: python312
questions:
- A broken precondition blames which side of the call, and a broken postcondition blames which side?
- Under Meyer's non-redundancy principle, why is checking the same condition again at every call site an anti-pattern?
created: 2026-07-04
---

## Brief

book has an unstated precondition and silently returns a negative number when it is violated. Add the require clause so misuse fails loud and the blame lands on the caller.

## Stub

```python
def book(seats_available, seats_requested):
    # TODO: require the precondition seats_requested <= seats_available, failing loud on violation
    return seats_available - seats_requested

print(book(10, 3))
try:
    book(2, 5)
except AssertionError as e:
    print("caller bug:", e)
```

## Solution

```python
def book(seats_available, seats_requested):
    assert seats_requested <= seats_available, "seats_requested must not exceed seats_available"
    return seats_available - seats_requested

print(book(10, 3))
try:
    book(2, 5)
except AssertionError as e:
    print("caller bug:", e)
```

## Expected Output

```
7
caller bug: seats_requested must not exceed seats_available
```
