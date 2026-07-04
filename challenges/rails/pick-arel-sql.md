---
wiki: rails/activerecord-pick
section: Raw SQL expressions
kind: write-code
env: rails
questions:
- What does Rails do with a plain "LENGTH(title)" string passed to pick, and what does Arel.sql change?
- When should you prefer a built-in method like count over pick(Arel.sql(...))?
created: 2026-07-03
---

## Brief

pick rejects the raw string because it is not a column name. Fix the call so the SQL expression reaches the database unquoted.

## Stub

```ruby
Article.transaction do
  Article.create!(title: "hello", published: true)
  # TODO: make pick accept the raw SQL expression LENGTH(title)
  puts Article.pick("LENGTH(title)")
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.transaction do
  Article.create!(title: "hello", published: true)
  puts Article.pick(Arel.sql("LENGTH(title)"))
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
5
```
