---
wiki: rails/delegated-type
section: What the delegated_type declaration generates
kind: predict-output
env: rails
questions:
- What does a typed accessor like entry.comment return when the entry holds a different type?
- Does the macro generate atomic creators like Entry.create_with_message!?
created: 2026-07-03
---

## Brief

One delegated_type declaration on an entry holding a Message payload. Predict what the predicate, the wrong-type accessor, the reflection helper, and the creator check each print.

## Stub

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) { |t| t.references :entryable, polymorphic: true }
conn.create_table(:messages, temporary: true) { |t| t.string :subject }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment]
end
class Message < ApplicationRecord; end
class Comment < ApplicationRecord; end

entry = Entry.new(entryable: Message.new(subject: "hi"))
puts entry.message?
puts entry.comment.inspect
puts entry.entryable_class
puts Entry.respond_to?(:create_with_message!)
```

## Solution

```ruby
conn = ActiveRecord::Base.connection
conn.create_table(:entries, temporary: true) { |t| t.references :entryable, polymorphic: true }
conn.create_table(:messages, temporary: true) { |t| t.string :subject }

class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment]
end
class Message < ApplicationRecord; end
class Comment < ApplicationRecord; end

entry = Entry.new(entryable: Message.new(subject: "hi"))
puts entry.message?
puts entry.comment.inspect
puts entry.entryable_class
puts Entry.respond_to?(:create_with_message!)
```

## Expected Output

```
true
nil
Message
false
```
