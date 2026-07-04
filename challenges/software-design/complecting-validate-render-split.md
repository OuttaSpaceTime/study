---
wiki: software-design/software-complexity
section: "Complecting, when two simple things become one expensive one"
kind: write-code
questions:
- Why did the combined function look simple right up until the batch job appeared?
- What did every existing caller of the combined function have to pay once the split became necessary?
env: python312
created: 2026-07-03
---

## Brief

render_invoice braids business validation together with HTML rendering. A nightly batch job now needs the validation with no HTML involved at all. Decomplect the two concerns so the batch loop can validate alone.

## Stub

```python
def render_invoice(invoice):
    if invoice["total"] < 0:
        raise ValueError("negative total")
    return f"<p>Invoice #{invoice['id']}: {invoice['total']}</p>"

# TODO: split render_invoice into validate_invoice and render_invoice
# so the batch loop below can validate without building any HTML

for invoice in [{"id": 1, "total": 40}, {"id": 2, "total": -5}]:
    try:
        validate_invoice(invoice)
        print("ok", invoice["id"])
    except ValueError as error:
        print("rejected", invoice["id"], error)

print(render_invoice({"id": 1, "total": 40}))
```

## Solution

```python
def validate_invoice(invoice):
    if invoice["total"] < 0:
        raise ValueError("negative total")

def render_invoice(invoice):
    return f"<p>Invoice #{invoice['id']}: {invoice['total']}</p>"

for invoice in [{"id": 1, "total": 40}, {"id": 2, "total": -5}]:
    try:
        validate_invoice(invoice)
        print("ok", invoice["id"])
    except ValueError as error:
        print("rejected", invoice["id"], error)

print(render_invoice({"id": 1, "total": 40}))
```

## Expected Output

```
ok 1
rejected 2 negative total
<p>Invoice #1: 40</p>
```
