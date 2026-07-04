---
wiki: rails/delegated-type
section: Schema Shape
kind: write-code
env: rails
questions:
- Why does the entries table need entryable_type in addition to entryable_id?
- Which table holds the shared attributes and which holds the variant payload?
created: 2026-07-03
---

## Brief

The parent table must record which subtype table to look in and which row inside it. Add the single migration line that produces both columns.

## Stub

```ruby
conn = ActiveRecord::Base.connection
conn.create_table :entries, temporary: true do |t|
  t.string :title
  # TODO: one line that lets an entry point at a row in any subtype table
end
puts conn.columns(:entries).map(&:name).sort.join(", ")
```

## Solution

```ruby
conn = ActiveRecord::Base.connection
conn.create_table :entries, temporary: true do |t|
  t.string :title
  t.references :entryable, polymorphic: true
end
puts conn.columns(:entries).map(&:name).sort.join(", ")
```

## Expected Output

```
entryable_id, entryable_type, id, title
```
