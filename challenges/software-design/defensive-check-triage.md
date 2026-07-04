---
wiki: software-design/software-complexity
section: Triaging defensive checks, especially in AI-generated code
kind: write-code
env: python312
questions:
- What concrete guarantee makes the removed check provably dead, and where in the code does it live?
- Why must the other check stay even though no caller in sight passes a bad value?
created: 2026-07-04
---

## Brief

An agent wrote convert with two defensive checks that look equally careful. Trace outward for a concrete guarantee and delete exactly the one check whose guarded case is provably impossible.

## Stub

```python
def fetch_rate(currency):
    rates = {"EUR": 0.92, "GBP": 0.79}
    if currency not in rates:
        raise KeyError(f"unknown currency: {currency}")
    return rates[currency]

def convert(amount, currency):
    rate = fetch_rate(currency)
    # TODO: one of the two checks below guards an impossible case,
    # delete that one and keep the other
    if rate is None:
        return None
    if amount < 0:
        return None
    return round(amount * rate, 2)

print(convert(100, "EUR"))
print(convert(-5, "EUR"))
```

## Solution

```python
def fetch_rate(currency):
    rates = {"EUR": 0.92, "GBP": 0.79}
    if currency not in rates:
        raise KeyError(f"unknown currency: {currency}")
    return rates[currency]

def convert(amount, currency):
    rate = fetch_rate(currency)
    if amount < 0:
        return None
    return round(amount * rate, 2)

print(convert(100, "EUR"))
print(convert(-5, "EUR"))
```

## Expected Output

```
92.0
None
```
