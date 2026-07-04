---
wiki: rails/delegated-type
section: Direction of Delegation
kind: write-code
env: rails
questions:
- Which direction does the delegated in the macro name refer to, and does the macro write any delegate for you?
- What happens to the data path if you skip the delegate line?
created: 2026-07-03
---

## Brief

The macro delegates nothing by itself, so message.title raises NoMethodError as written. Write the one line on the subtype that forwards the shared attribute up to the parent entry.

## Stub

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) do |t|
  t.string :title
  t.references :entryable, polymorphic: true
end
conn.create_table(:messages, temporary: true) { |t| t.string :subject }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message]
end
class Message < ApplicationRecord
  has_one :entry, as: :entryable
  # TODO: one line so message.title reads the shared attribute from the parent entry
end

message = Message.create!(subject: "hi")
Entry.create!(title: "Shared title", entryable: message)
puts message.title
```

## Solution

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) do |t|
  t.string :title
  t.references :entryable, polymorphic: true
end
conn.create_table(:messages, temporary: true) { |t| t.string :subject }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message]
end
class Message < ApplicationRecord
  has_one :entry, as: :entryable
  delegate :title, to: :entry
end

message = Message.create!(subject: "hi")
Entry.create!(title: "Shared title", entryable: message)
puts message.title
```

## Expected Output

```
Shared title
```
