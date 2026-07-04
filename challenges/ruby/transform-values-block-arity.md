---
wiki: ruby/transform-values
section: The block receives only the value
kind: predict-output
env: ruby
questions:
- What does the transform_values block yield, and what ends up in a second block parameter?
- What is the signal that you should reach for a different method than transform_values?
created: 2026-07-04
---

## Brief

The author expects the key and value in the block. Predict what actually gets printed.

## Stub

```ruby
h = { a: 1, b: 2 }
p h.transform_values { |k, v| "#{k}:#{v}" }
```

## Solution

```ruby
h = { a: 1, b: 2 }
p h.transform_values { |k, v| "#{k}:#{v}" }
```

## Expected Output

```
{a: "1:", b: "2:"}
```
