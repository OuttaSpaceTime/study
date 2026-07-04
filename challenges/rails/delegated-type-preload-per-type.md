---
wiki: rails/delegated-type
section: N+1 Gotcha
kind: predict-output
env: rails
questions:
- What does the preloaded query count scale with, given it is not the row count?
- How do you preload when you only care about one variant type?
created: 2026-07-03
---

## Brief

Four entries split across two subtype tables, then the payload of each is touched twice. Predict the SELECT count for the naive loop and for the loop with includes(:entryable).

## Stub

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) { |t| t.references :entryable, polymorphic: true }
conn.create_table(:messages, temporary: true) { |t| t.string :subject }
conn.create_table(:comments, temporary: true) { |t| t.string :content }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment]
end
class Message < ApplicationRecord; end
class Comment < ApplicationRecord; end

2.times { |i| Entry.create!(entryable: Message.create!(subject: "m#{i}")) }
2.times { |i| Entry.create!(entryable: Comment.create!(content: "c#{i}")) }

selects = 0
ActiveSupport::Notifications.subscribe("sql.active_record") do |event|
  selects += 1 if event.payload[:sql].start_with?("SELECT")
end

Entry.all.each { |e| e.entryable }
puts selects

selects = 0
Entry.includes(:entryable).each { |e| e.entryable }
puts selects
```

## Solution

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) { |t| t.references :entryable, polymorphic: true }
conn.create_table(:messages, temporary: true) { |t| t.string :subject }
conn.create_table(:comments, temporary: true) { |t| t.string :content }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment]
end
class Message < ApplicationRecord; end
class Comment < ApplicationRecord; end

2.times { |i| Entry.create!(entryable: Message.create!(subject: "m#{i}")) }
2.times { |i| Entry.create!(entryable: Comment.create!(content: "c#{i}")) }

selects = 0
ActiveSupport::Notifications.subscribe("sql.active_record") do |event|
  selects += 1 if event.payload[:sql].start_with?("SELECT")
end

Entry.all.each { |e| e.entryable }
puts selects

selects = 0
Entry.includes(:entryable).each { |e| e.entryable }
puts selects
```

## Expected Output

```
5
3
```
