---
wiki: rails/database-transactions
section: Rails rollback-on-exception
kind: predict-output
env: rails
questions:
- What would this script print if the raise were a RuntimeError instead of ActiveRecord::Rollback?
- Why can the caller of this transaction block not tell that anything went wrong?
created: 2026-07-03
---

## Brief

A record is created inside a transaction block that then raises ActiveRecord::Rollback. Predict whether the script crashes and what the two puts lines print.

## Stub

```ruby
result = Article.transaction do
  Article.create!(title: "Draft")
  raise ActiveRecord::Rollback
end
puts result.inspect
puts Article.count
```

## Solution

```ruby
result = Article.transaction do
  Article.create!(title: "Draft")
  raise ActiveRecord::Rollback
end
puts result.inspect
puts Article.count
```

## Expected Output

```
nil
0
```
