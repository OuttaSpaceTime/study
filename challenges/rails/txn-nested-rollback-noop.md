---
wiki: rails/database-transactions
section: Nested transactions and savepoints
kind: predict-output
env: rails
questions:
- Which option makes the inner block emit a real SAVEPOINT, and what would the printed title be with it?
- Why does the outer block never notice the raise inside the inner block?
created: 2026-07-03
---

## Brief

A bare transaction block is nested inside another and the inner one raises ActiveRecord::Rollback. Predict the title printed after the inner block. The final rollback only cleans up the shared database.

## Stub

```ruby
Article.transaction do
  article = Article.create!(title: "A")
  Article.transaction do
    article.update!(title: "B")
    raise ActiveRecord::Rollback
  end
  puts article.reload.title
  raise ActiveRecord::Rollback
end
puts Article.count
```

## Solution

```ruby
Article.transaction do
  article = Article.create!(title: "A")
  Article.transaction do
    article.update!(title: "B")
    raise ActiveRecord::Rollback
  end
  puts article.reload.title
  raise ActiveRecord::Rollback
end
puts Article.count
```

## Expected Output

```
B
0
```
