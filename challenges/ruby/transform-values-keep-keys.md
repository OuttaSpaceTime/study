---
wiki: ruby/transform-values
section: What transform_values does and why it preserves keys
kind: write-code
env: ruby
questions:
- Which hash method means keep keys, change values, and what does it return?
- Why is each_with_object or map plus to_h considered a workaround for this job?
created: 2026-07-04
---

## Brief

Double every price while keeping the keys untouched. Use the dedicated verb for this, not a hash rebuild.

## Stub

```ruby
prices = { apple: 100, pear: 200 }
doubled = prices # TODO: double each value, keep the keys, return a new Hash
p doubled
```

## Solution

```ruby
prices = { apple: 100, pear: 200 }
doubled = prices.transform_values { |v| v * 2 }
p doubled
```

## Expected Output

```
{apple: 200, pear: 400}
```
