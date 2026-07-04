---
wiki: rails/activerecord-pick
section: What pick returns and when it stops scanning
kind: predict-output
env: rails
questions:
- Why does pick(:title) return a bare string while pick(:title, :published) returns an array?
- What clause does pick add to the SQL so the database stops after the first matching row?
created: 2026-07-03
---

## Brief

Two articles match the scope. Predict the shape of each pick result: scalar or array, and which row it comes from.

## Stub

```ruby
Article.transaction do
  Article.create!(title: "First", published: true)
  Article.create!(title: "Second", published: true)
  p Article.order(:title).pick(:title)
  p Article.order(:title).pick(:title, :published)
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.transaction do
  Article.create!(title: "First", published: true)
  Article.create!(title: "Second", published: true)
  p Article.order(:title).pick(:title)
  p Article.order(:title).pick(:title, :published)
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
"First"
["First", true]
```
