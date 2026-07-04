---
wiki: rails/upsert-and-concurrent-inserts
section: Rails create!, insert_all, insert_all!, upsert_all
kind: predict-output
env: rails
questions:
- Which conflict clause does each of insert_all, insert_all!, and upsert_all emit?
- How does the bang convention get twisted here compared to create vs create!?
created: 2026-07-03
---

## Brief

Row id 1 exists, then three bulk calls hit the same id. Predict what each p prints and whether the bang call raises.

## Stub

```ruby
Article.transaction do
  Article.insert_all([{ id: 1, title: "original" }])
  Article.insert_all([{ id: 1, title: "skipped?" }])
  p Article.pluck(:id, :title)
  Article.upsert_all([{ id: 1, title: "updated?" }])
  p Article.pluck(:id, :title)
  begin
    Article.insert_all!([{ id: 1, title: "bang" }])
  rescue ActiveRecord::RecordNotUnique
    puts "insert_all! raised RecordNotUnique"
  end
  raise ActiveRecord::Rollback
end
```

## Solution

```ruby
Article.transaction do
  Article.insert_all([{ id: 1, title: "original" }])
  Article.insert_all([{ id: 1, title: "skipped?" }])
  p Article.pluck(:id, :title)
  Article.upsert_all([{ id: 1, title: "updated?" }])
  p Article.pluck(:id, :title)
  begin
    Article.insert_all!([{ id: 1, title: "bang" }])
  rescue ActiveRecord::RecordNotUnique
    puts "insert_all! raised RecordNotUnique"
  end
  raise ActiveRecord::Rollback
end
```

## Expected Output

```
[[1, "original"]]
[[1, "updated?"]]
insert_all! raised RecordNotUnique
```
