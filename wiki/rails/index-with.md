---
title: index_with
aliases:
- Enumerable index_with
- ActiveSupport index_with
tags:
- ruby
- rails
- active-support
- enumerable
created: '2026-04-10'
updated: '2026-04-10'
source_skill: study-walkthrough
flashcard_ids: []
next_review: '2026-08-06'
review_interval: 30
probe_sections:
- Fixed Value vs Block
- index_with vs index_by
- index_with vs to_h
- Duplicate Keys
last_probed:
- index_with vs index_by
- index_with vs to_h
- Duplicate Keys
- Fixed Value vs Block
---

# index_with

Active Support method on `Enumerable` that builds a hash where **keys are the original elements** and **values come from a block or fixed argument**. It's the inverse of `index_by`, which lets the block control the keys.

## Fixed Value vs Block

```ruby
# Fixed value: every key gets the same value
[:read, :write, :admin].index_with(false)
# => { read: false, write: false, admin: false }

# Block — computed per element
[:name, :age].index_with { |attr| user.public_send(attr) }
# => { name: "Alice", age: 30 }
```

## index_with vs index_by

The block controls different sides of the hash:

- **`index_by`**: block picks the **key**, value is the original element
- **`index_with`**: element is the **key**, block picks the value

```ruby
users.index_by(&:email)
# => { "alice@ex.com" => #<User>, "bob@ex.com" => #<User> }

[:name, :age].index_with { |a| "default_#{a}" }
# => { name: "default_name", age: "default_age" }
```

## index_with vs to_h

`to_h` is `stdlib` Ruby and requires explicit `[key, value]` pairs:

```ruby
statuses.to_h { |s| [s, 0] }     # stdlib
statuses.index_with(0)           # Active Support — cleaner
```

Use `to_h` outside Rails; use `index_with` when Active Support is available.

## Duplicate Keys

Hash keys are unique. Thus duplicates are silently overwritten. Use `index_with` with collections that have **unique elements** (enum values, column names, permission keys).

```ruby
["a", "b", "a"].index_with { |x| x.upcase }
# => { "a" => "A", "b" => "B" }  # first "a" entry lost
```

## Related Concepts

- [[rails/activerecord-pick]]: another concise ActiveRecord/ActiveSupport query method
