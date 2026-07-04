---
wiki: openapi/schema-composition
section: The oneOf Shared-Field Trap
kind: write-code
env: python312
questions:
- Why does a payload containing only amount match both payment schemas before the fix?
- What does an OpenAPI discriminator require of each schema listed under oneOf?
created: 2026-07-03
---

## Brief

Both payment schemas share the amount field, so a credit card payload matches both and oneOf rejects it. Fix the bank transfer schema with the discriminator check so exactly one schema matches.

## Stub

```python
def valid_one_of(schemas, payload):
    return sum(1 for matches in schemas if matches(payload)) == 1

def credit_card(p):
    return "amount" in p and p.get("payment_type") == "credit_card"

def bank_transfer(p):
    return "amount" in p  # TODO: also require the discriminator value "bank_transfer"

print(valid_one_of([credit_card, bank_transfer], {"amount": 9.99, "payment_type": "credit_card"}))
print(valid_one_of([credit_card, bank_transfer], {"amount": 9.99}))
```

## Solution

```python
def valid_one_of(schemas, payload):
    return sum(1 for matches in schemas if matches(payload)) == 1

def credit_card(p):
    return "amount" in p and p.get("payment_type") == "credit_card"

def bank_transfer(p):
    return "amount" in p and p.get("payment_type") == "bank_transfer"

print(valid_one_of([credit_card, bank_transfer], {"amount": 9.99, "payment_type": "credit_card"}))
print(valid_one_of([credit_card, bank_transfer], {"amount": 9.99}))
```

## Expected Output

```
True
False
```
