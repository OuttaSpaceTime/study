---
wiki: rails/upsert-and-concurrent-inserts
section: Bulk methods bypass validations and callbacks
kind: predict-output
env: rails
questions:
- Why does insert_all ignore the presence validation that stopped create?
- Where must the integrity guarantee live once bulk methods bypass the model layer?
created: 2026-07-03
---

## Brief

A presence validation on title guards the model. Both writes push a row with a nil title. Predict the two counts.

## Stub

```ruby
Article.validates :title, presence: true

ActiveRecord::Base.transaction do
  Article.create(title: nil, body: "draft")
  puts Article.count
  Article.insert_all([{ title: nil, body: "draft" }])
  puts Article.count
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.validates :title, presence: true

ActiveRecord::Base.transaction do
  Article.create(title: nil, body: "draft")
  puts Article.count
  Article.insert_all([{ title: nil, body: "draft" }])
  puts Article.count
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
0
1
```
