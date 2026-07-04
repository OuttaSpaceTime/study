---
wiki: openapi/schema-composition
section: The additionalProperties Trap
kind: predict-output
env: python312
questions:
- Which subschema rejects the name key, and why does it never see the other subschema's properties?
- Where does additionalProperties false have to live so the composed shape validates?
created: 2026-07-03
---

## Brief

This minimal validator evaluates additionalProperties per subschema, exactly as the JSON Schema spec does. Predict the result for each payload.

## Stub

```python
def validate(schema, payload):
    if "allOf" in schema:
        return all(validate(sub, payload) for sub in schema["allOf"])
    if schema.get("additionalProperties", True) is False:
        return all(key in schema.get("properties", {}) for key in payload)
    return True

composed = {"allOf": [
    {"properties": {"id": {}}, "additionalProperties": False},
    {"properties": {"name": {}}},
]}

print(validate(composed, {"id": "abc"}))
print(validate(composed, {"id": "abc", "name": "widget"}))
```

## Solution

```python
def validate(schema, payload):
    if "allOf" in schema:
        return all(validate(sub, payload) for sub in schema["allOf"])
    if schema.get("additionalProperties", True) is False:
        return all(key in schema.get("properties", {}) for key in payload)
    return True

composed = {"allOf": [
    {"properties": {"id": {}}, "additionalProperties": False},
    {"properties": {"name": {}}},
]}

print(validate(composed, {"id": "abc"}))
print(validate(composed, {"id": "abc", "name": "widget"}))
```

## Expected Output

```
True
False
```
