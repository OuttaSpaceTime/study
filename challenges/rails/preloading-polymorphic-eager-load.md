---
wiki: rails/activerecord-preloading
section: Polymorphic associations
kind: predict-output
env: rails
questions:
- Why can preload handle a polymorphic belongs_to when eager_load cannot?
- How many queries does preload fire when the parent set contains two distinct entryable types?
created: 2026-07-03
---

## Brief

A polymorphic belongs_to, loaded once with eager_load and once with preload. Predict what each line prints.

## Stub

```ruby
ActiveRecord::Base.connection.create_table(:entries, temporary: true) { |t| t.string :entryable_type; t.integer :entryable_id }
class Entry < ActiveRecord::Base; belongs_to :entryable, polymorphic: true; end

begin
  Entry.eager_load(:entryable).to_a
rescue => e
  puts e.class
end
puts Entry.preload(:entryable).to_a.size
```

## Solution

```ruby
ActiveRecord::Base.connection.create_table(:entries, temporary: true) { |t| t.string :entryable_type; t.integer :entryable_id }
class Entry < ActiveRecord::Base; belongs_to :entryable, polymorphic: true; end

begin
  Entry.eager_load(:entryable).to_a
rescue => e
  puts e.class
end
puts Entry.preload(:entryable).to_a.size
```

## Expected Output

```
PLACEHOLDER
```
