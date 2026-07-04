---
wiki: rails/activerecord-pick
section: nil on no match and chaining with scopes
kind: predict-output
env: rails
questions:
- Why does the multi-column pick also return nil instead of an empty array?
- Where does the LIMIT 1 land when pick is called on a chained scope?
created: 2026-07-03
---

## Brief

The table is empty, so the chained scope matches nothing. Predict all three lines, including the multi-column case.

## Stub

```ruby
scope = Article.where(published: true).order(:title)
p scope.pick(:title)
p scope.pick(:id, :title)
p scope.pick(:title)&.upcase
```

## Solution

```ruby
scope = Article.where(published: true).order(:title)
p scope.pick(:title)
p scope.pick(:id, :title)
p scope.pick(:title)&.upcase
```

## Expected Output

```
nil
nil
nil
```
