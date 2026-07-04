---
wiki: openapi/schema-composition
section: anyOf vs oneOf
kind: predict-output
env: python312
questions:
- Why can anyOf short-circuit on the first match while oneOf must validate against every listed schema?
- When would you deliberately pick anyOf over oneOf in an API spec?
created: 2026-07-03
---

## Brief

Two overlapping schemas, three values. Predict for each value whether anyOf accepts it and whether oneOf accepts it.

## Stub

```python
schemas = [
    lambda v: isinstance(v, str) and "@" in v,
    lambda v: isinstance(v, str) and len(v) >= 3,
]

for value in ["felix@example.org", "bob", 42]:
    hits = sum(1 for matches in schemas if matches(value))
    print(f"{value!r}: anyOf={hits >= 1} oneOf={hits == 1}")
```

## Solution

```python
schemas = [
    lambda v: isinstance(v, str) and "@" in v,
    lambda v: isinstance(v, str) and len(v) >= 3,
]

for value in ["felix@example.org", "bob", 42]:
    hits = sum(1 for matches in schemas if matches(value))
    print(f"{value!r}: anyOf={hits >= 1} oneOf={hits == 1}")
```

## Expected Output

```
'felix@example.org': anyOf=True oneOf=False
'bob': anyOf=True oneOf=True
42: anyOf=False oneOf=False
```
