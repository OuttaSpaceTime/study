---
wiki: rails/activerecord-pick
section: Multiple aggregates in one query
kind: write-code
env: rails
questions:
- Why is this one pick call better than calling count twice on the scope?
- What would select(...) return here instead, and what extra step would it force?
created: 2026-07-03
---

## Brief

Three articles, one published. Fetch the total count and the unpublished count in a single database round-trip.

## Stub

```ruby
Article.transaction do
  Article.create!(title: "A", published: true)
  Article.create!(title: "B", published: false)
  Article.create!(title: "C", published: false)
  # TODO: one query returning [total, drafts] via pick
  total, drafts = Article.pick(...)
  p [total, drafts]
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.transaction do
  Article.create!(title: "A", published: true)
  Article.create!(title: "B", published: false)
  Article.create!(title: "C", published: false)
  total, drafts = Article.pick(
    Arel.sql("COUNT(*), COUNT(*) FILTER (WHERE NOT published)")
  )
  p [total, drafts]
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
[3, 2]
```
