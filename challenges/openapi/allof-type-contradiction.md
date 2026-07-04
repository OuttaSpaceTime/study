---
wiki: openapi/schema-composition
section: allOf Is Not Inheritance
kind: predict-output
env: python312
questions:
- Why can no payload ever satisfy this composition?
- What error does spec tooling raise for this contradiction?
created: 2026-07-03
---

## Brief

BaseEntity declares id as a string and the extension redeclares id as an integer. If allOf worked like inheritance the extension would override the base. Predict which payload validates.

## Stub

```python
def base_entity(p):
    return isinstance(p.get("id"), str)

def extension(p):
    return isinstance(p.get("id"), int)

for payload in [{"id": "abc"}, {"id": 42}]:
    print(base_entity(payload) and extension(payload))
```

## Solution

```python
def base_entity(p):
    return isinstance(p.get("id"), str)

def extension(p):
    return isinstance(p.get("id"), int)

for payload in [{"id": "abc"}, {"id": 42}]:
    print(base_entity(payload) and extension(payload))
```

## Expected Output

```
False
False
```
