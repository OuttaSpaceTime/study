---
wiki: rails/activerecord-pick
section: vs pluck
kind: predict-output
env: rails
questions:
- Which of the two queries carries LIMIT 1, and why is pick cheaper than pluck(...).first?
- What does each method return when the scope matches no rows?
created: 2026-07-03
---

## Brief

The same ordered scope, queried once with pick and once with pluck. Predict both results.

## Stub

```ruby
Article.transaction do
  Article.create!(title: "Alpha", published: true)
  Article.create!(title: "Beta", published: true)
  scope = Article.where(published: true).order(:title)
  p scope.pick(:title)
  p scope.pluck(:title)
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.transaction do
  Article.create!(title: "Alpha", published: true)
  Article.create!(title: "Beta", published: true)
  scope = Article.where(published: true).order(:title)
  p scope.pick(:title)
  p scope.pluck(:title)
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
"Alpha"
["Alpha", "Beta"]
```
