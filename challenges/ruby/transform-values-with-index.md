---
wiki: ruby/transform-values
section: with_index for positional info
kind: write-code
env: ruby
questions:
- What does transform_values return when called without a block, and why does that matter here?
created: 2026-07-04
---

## Brief

Add each value's position (0, 1, 2) to the value itself. Stay in Hash-land by chaining off transform_values.

## Stub

```ruby
h = { a: 10, b: 20, c: 30 }
result = h # TODO: add each value's index to it via transform_values
p result
```

## Solution

```ruby
h = { a: 10, b: 20, c: 30 }
result = h.transform_values.with_index { |v, i| v + i }
p result
```

## Expected Output

```
{a: 10, b: 21, c: 32}
```
