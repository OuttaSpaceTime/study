---
title: ActiveRecord pick
aliases:
- pick
- pick vs pluck
- rails pick
tags:
- rails
- activerecord
- sql
created: '2026-04-09'
updated: '2026-04-09'
source_skill: study-card
next_review: '2026-05-11'
review_interval: 12
probe_sections:
- Behavior
- vs pluck
- Raw SQL expressions
- Multiple aggregates in one query
- Gotchas
last_probed:
- Multiple aggregates in one query
- Gotchas
- Behavior
- vs pluck
- Raw SQL expressions
---

# ActiveRecord pick

## TL;DR

`pick(*columns)` fetches column values from the **first matching row** with `LIMIT 1`.
Returns a scalar (one column) or flat array (multiple columns). Returns `nil` on no match.

## Behavior

```ruby
# single column → scalar
User.where(active: true).pick(:email)
# => "alice@example.com"

# multiple columns → flat array
User.where(active: true).pick(:id, :email)
# => [1, "alice@example.com"]

# no match → nil (not [])
User.where(active: false).pick(:email)
# => nil
```

## vs pluck

| | `pick` | `pluck` |
|---|---|---|
| SQL | adds `LIMIT 1` | no limit |
| returns | scalar or flat array | array of all results |
| no match | `nil` | `[]` |

`pick` is equivalent to `pluck(...).first` but more efficient — the database stops after one row rather than fetching all matching rows into Ruby.

## Raw SQL expressions

Use `Arel.sql` to pass SQL expressions instead of column names:

```ruby
user_scope.pick(Arel.sql("SUM(points)"))
# => 1500
```

Without `Arel.sql`, Rails quotes the string as a column name (`SELECT "SUM(points)" FROM users`), producing an invalid query. `Arel.sql` marks the string as already-safe SQL, bypassing quoting.

Prefer built-in AR methods over `Arel.sql` when they exist — `pick(Arel.sql("COUNT(*)"))` is redundant since `scope.count` is cleaner and equivalent.

## Multiple aggregates in one query

`pick` shines when you need several aggregate values in a single DB round-trip:

```ruby
message_count, unread_count = inbox_scope.pick(
  Arel.sql('COUNT(*), COUNT(*) FILTER (WHERE NOT read)')
)
```

The alternatives are worse: two separate queries hit the DB twice, and `select` returns a relation of AR objects requiring `.first` to extract the row:

```ruby
# two queries
message_count = inbox_scope.count
unread_count  = inbox_scope.where(read: false).count

# one query via select — but verbose and instantiates AR objects
row = inbox_scope.select(Arel.sql(
  'COUNT(*) AS message_count, COUNT(*) FILTER (WHERE NOT read) AS unread_count'
)).first
message_count = row["message_count"]
unread_count  = row["unread_count"]
```

## Gotchas

- Returns `nil` on no match — guard before calling methods on the result
- Chainable with scopes, `where`, `order` — `LIMIT 1` appends to the full query
- `LIMIT 1` is always added even when redundant (e.g. `COUNT(*)` already returns one row)
