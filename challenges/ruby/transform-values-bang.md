---
wiki: ruby/transform-values
section: Bang variant
kind: predict-output
env: ruby
questions:
- How do transform_values and transform_values! differ in what happens to the receiver?
created: 2026-07-04
---

## Brief

The same block runs twice, once without and once with the bang. Predict both printed hashes.

## Stub

```ruby
h = { a: 1, b: 2 }
h.transform_values { |v| v * 2 }
p h
h.transform_values! { |v| v * 2 }
p h
```

## Solution

```ruby
h = { a: 1, b: 2 }
h.transform_values { |v| v * 2 }
p h
h.transform_values! { |v| v * 2 }
p h
```

## Expected Output

```
{a: 1, b: 2}
{a: 2, b: 4}
```
