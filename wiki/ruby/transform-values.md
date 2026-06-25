---
title: transform_values
aliases:
- transform_values
- ruby transform_values
- hash transform values
tags:
- ruby
- hash
- enumerable
created: '2026-04-17'
updated: '2026-04-17'
source_skill: study-walkthrough
probe_sections:
- What transform_values does and why it preserves keys
- vs map on a hash
- The block receives only the value
- Bang variant
- with_index for positional info
- When not to use it
last_probed:
- What transform_values does and why it preserves keys
- with_index for positional info
- When not to use it
- vs map on a hash
- The block receives only the value
- Bang variant
review_interval: 34
next_review: '2026-07-17'
flashcard_ids: []
---

# transform_values

## TL;DR

`transform_values` applies a block to each value of a hash, **keeps keys untouched**, and returns a **new Hash** of the same shape. It is the dedicated verb for "keep keys, change values". A structure-preserving map that stays in Hash-land.

```ruby
{ apple: 100, pear: 200 }.transform_values { |v| v * 1.1 }
# => { apple: 110.0, pear: 220.0 }
```

Added in Ruby 2.4.

## What transform_values does and why it preserves keys

A hash is a set of `key => value` pairs. Most hash operations want one of:

1. Change the values, keep the keys: `transform_values`
2. Change the keys, keep the values: `transform_keys`
3. Change both, or change the shape (to Array, etc.): `map`

`transform_values` exists because "keep keys, change values" is extremely common, and the alternatives (`each_with_object`, `map` + `to_h`) mix concerns. You end up writing code about *rebuilding a hash* instead of code about *transforming values*.

## vs map on a hash

`map` escapes to Array-land. `transform_values` stays in Hash-land.

```ruby
h = { a: 1, b: 2 }

h.transform_values { |v| v * 2 }
# => { a: 2, b: 4 }            # Hash

h.map { |k, v| [k, v * 2] }
# => [ [:a, 2], [:b, 4] ]        # Array of pairs!

h.map { |k, v| [k, v * 2] }.to_h
# => { a: 2, b: 4 }            # Hash, but verbose
```

The `map { ... }.to_h` pattern was the pre-2.4 workaround. `transform_values` replaces it with a single, intention-revealing call.

## The block receives only the value

The block yields **just the value**. Not the key:

```ruby
# correct
h.transform_values { |v| v.to_s }

# wrong — k is nil, v gets the value
h.transform_values { |k, v| "#{k}: #{v}" }
```

If you need the key inside the block, that is the signal to reach for a different method:

```ruby
h.each_with_object({}) { |(k, v), memo| memo[k] = "#{k}=#{v}" }
# or
h.map { |k, v| [k, "#{k}=#{v}"] }.to_h
```

## Bang variant

`transform_values!` mutates the receiver in place; non-bang returns a new hash.

```ruby
h = { a: 1, b: 2 }
h.transform_values { |v| v * 2 }   # => { a: 2, b: 4 }, h unchanged
h.transform_values! { |v| v * 2 }  # => { a: 2, b: 4 }, h mutated
```

## with_index for positional info

Calling `transform_values` without a block returns an Enumerator, which chains with `with_index`:

```ruby
{ a: 1, b: 2 }.transform_values.with_index { |v, i| v + i }
# => { a: 1, b: 3 }
```

Handy when the transform depends on the value *and* its position.

## When not to use it

- **Need the key** in the transform → `each_with_object` or `map` + `to_h`
- **Want to drop pairs** (filter) → `select` first, then `transform_values`; or `filter_map` + `to_h`
- **Want a different structure** (Array, nested Hash) → `map`
- **Need to change keys too** → chain with `transform_keys`, or use `map` + `to_h` if both depend on each other

```ruby
h.transform_keys(&:to_s).transform_values { |v| v * 2 }
```

## Related Concepts

- [[rails/activerecord-pick]]: another "dedicated verb" pattern that replaces a verbose combination (`pluck(...).first`) with a single intention-revealing call
