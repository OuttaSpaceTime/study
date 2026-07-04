---
wiki: ruby/transform-values
section: vs map on a hash
kind: predict-output
env: ruby
questions:
- What structure does map return when called on a hash?
- How did people get a transformed hash back before transform_values existed?
created: 2026-07-04
---

## Brief

Both lines transform the same hash. Predict the return structure of each.

## Stub

```ruby
h = { a: 1, b: 2 }
p h.transform_values { |v| v * 2 }
p h.map { |k, v| [k, v * 2] }
```

## Solution

```ruby
h = { a: 1, b: 2 }
p h.transform_values { |v| v * 2 }
p h.map { |k, v| [k, v * 2] }
```

## Expected Output

```
{a: 2, b: 4}
[[:a, 2], [:b, 4]]
```
