---
wiki: rails/delegated-type
section: What `delegated_type` Expands To
kind: write-code
env: rails
questions:
- Which generated symbols are real associations and which are plain scopes?
- Why does includes(:messages) raise AssociationNotFoundError while includes(:entryable) works?
created: 2026-07-03
---

## Brief

Entry.messages is not an association. It is a SQL filter that delegated_type generates for you. Hand-roll that scope on a plain polymorphic belongs_to.

## Stub

```ruby
ActiveRecord::Base.connection.create_table(:entries, temporary: true) do |t|
  t.references :entryable, polymorphic: true
end

class Entry < ApplicationRecord
  belongs_to :entryable, polymorphic: true
  # TODO: hand-roll the :messages type scope that delegated_type would generate
end

puts Entry.messages.to_sql
```

## Solution

```ruby
ActiveRecord::Base.connection.create_table(:entries, temporary: true) do |t|
  t.references :entryable, polymorphic: true
end

class Entry < ApplicationRecord
  belongs_to :entryable, polymorphic: true
  scope :messages, -> { where(entryable_type: "Message") }
end

puts Entry.messages.to_sql
```

## Expected Output

```
SELECT "entries".* FROM "entries" WHERE "entries"."entryable_type" = 'Message'
```
