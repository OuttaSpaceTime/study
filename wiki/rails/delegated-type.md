---
title: Delegated Type
aliases:
- delegated_type
- delegated types
- delegated_type macro
- Rails delegated type
tags:
- rails
- activerecord
- polymorphism
created: '2026-04-17'
updated: '2026-06-10'
source_skill: study-walkthrough
last_deepened: '2026-04-17'
next_review: '2026-07-31'
review_interval: 30
flashcard_ids: []
---

# Delegated Type

A Rails pattern for modeling heterogeneous subtypes that **share some fields but have different payload schemas**. A "superclass" table holds the shared attributes; each variant lives in its own table. The parent row points to the variant row via a polymorphic association, and variants delegate shared-attribute reads *back up* to the parent.

It's the answer to "STI would work but the variants diverge too much in schema" and to "polymorphic associations alone make cross-type queries awkward."

## The Problem It Solves

Modeling `Entry` with variants `Message`, `Comment`, `Post`:

- **Fat table** (one table, nullable columns per variant): NULL-heavy, no schema discipline.
- **STI** (`type` column, one table): variants must share the schema. Adding variant-specific columns bloats the table.
- **Polymorphic only**: flexible, but shared attributes (`account_id`, `created_at`) scatter across subtype tables, so "all entries this week across types" requires UNIONs.
- **Delegated type**: shared attrs on the parent, variant attrs on the subtype. Use one indexable, queryable parent table plus clean per-variant tables.

## Schema Shape

```
accounts:  id, name
entries:   id, account_id, entryable_type, entryable_id, created_at
messages:  id, subject, body
comments:  id, content
```

The `entries` row holds:
- `entryable_id`: the row id in the subtype table
- `entryable_type`: string like `"Message"` / `"Comment"` telling Rails which table

Both are needed. An id alone is ambiguous across multiple subtype tables.

## What the delegated_type declaration generates

```ruby
class Entry < ApplicationRecord
  belongs_to :account
  delegated_type :entryable, types: %w[ Message Comment ], dependent: :destroy
end

module Entryable
  extend ActiveSupport::Concern
  included do
    has_one :entry, as: :entryable, touch: true
    delegate :account, to: :entry
  end
end

class Message < ApplicationRecord
  include Entryable
end
```

`delegated_type :entryable, types: [...]` generates:

1. `belongs_to :entryable, polymorphic: true`
2. Scopes: `Entry.messages`, `Entry.comments`
3. Type predicates: `entry.message?`, `entry.comment?`
4. Typed accessors: `entry.message` / `entry.comment` (return the entryable when it's that type, else `nil`) plus `entry.message_id` / `entry.comment_id`
5. Reflection helpers: `entry.entryable_class` (e.g. `Message`) and `entry.entryable_name` (e.g. `"message"`)

It does **not** generate atomic creators. `Entry.create_with_message!(...)` is **not** a default method. The macro produces no `create_with_*` at all. The Rails docs show it as a factory method you define yourself; if you want atomic subtype-plus-parent creation, you write it (see below).

## What `delegated_type` Expands To

`delegated_type` is a **declaration macro**, not an association itself. But it generates one. The hand-rolled equivalent of `delegated_type :entryable, types: %w[Message Comment], dependent: :destroy`:

```ruby
class Entry < ApplicationRecord
  # 1. The polymorphic association — this IS an association
  belongs_to :entryable, polymorphic: true, dependent: :destroy

  # 2. Class-level type scopes — NOT associations; they're SQL filters
  scope :messages, -> { where(entryable_type: "Message") }
  scope :comments, -> { where(entryable_type: "Comment") }

  # 3. Instance-level type predicates
  def message?; entryable_type == "Message"; end
  def comment?; entryable_type == "Comment"; end

  # 4. Typed accessors + reflection helpers
  def message; entryable if message?; end
  def comment; entryable if comment?; end
  def entryable_class; entryable_type.constantize; end
end
```

Atomic creators are **not** part of this expansion. The macro does not generate them. If you want `Entry.create_with_message!`, you write it yourself:

```ruby
class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment], dependent: :destroy

  # Hand-written factory — NOT generated. Wraps subtype + parent insert in a transaction.
  def self.create_with_message!(attrs)
    transaction { create!(entryable: Message.create!(attrs)) }
  end
end
```

Know what's an association vs what's not. This matters for `includes`:

| Symbol | What it is | `includes(...)` works? |
| ------ | ---------- | ---------------------- |
| `:entryable` | polymorphic `belongs_to` | yes |
| `:messages`, `:comments` | scopes (SQL filters) | no (raises `AssociationNotFoundError`) |
| `:message?`, `:comment?` | predicate methods | no |

`delegated_type` itself sits next to `belongs_to` / `has_many` syntactically. It's a class-level declaration with side effects. Specifically, it's a **higher-order** declaration that, per variant type, expands into one polymorphic association plus a scope, a predicate, a typed accessor, and an id accessor, plus the `entryable_class` / `entryable_name` reflection helpers. It does **not** expand into creators; those are hand-written factories.

## Direction of Delegation

**Nothing is method-delegated by default in either direction.** The macro name oversells what it does. `delegated_type` generates the scaffolding (association, scopes, predicates, atomic creators); delegation is a **convention you write manually** using the `delegate` keyword. The "delegated" in the name describes the *intended pattern*, not an automatic mechanism.

What this means concretely:

```ruby
# Without manual delegation — both raise NoMethodError:
entry.subject       # → no method 'subject' on Entry
message.account     # → no method 'account' on Message
```

To make either side ergonomic you write the delegate yourself:

```ruby
# Parent → variant (often added on Entry for callers that hold an Entry)
class Entry < ApplicationRecord
  delegated_type :entryable, types: %w[Message Comment]
  delegate :subject, :body, :content, to: :entryable
end

# Variant → parent (the "delegated" in the macro name)
module Entryable
  extend ActiveSupport::Concern
  included do
    has_one :entry, as: :entryable, touch: true
    delegate :account, :created_at, to: :entry
  end
end
```

The "delegated" in the macro name refers to the **subtype → parent** direction specifically. Each subtype delegates *up* to the parent for shared attributes. `account_id` lives on `entries`, so without the up-delegate, callers would walk `.entry.account` manually.

```ruby
message.account          # works via delegate :account, to: :entry
message.entry.account    # same thing, explicit
```

The delegate is pure ergonomics. The data path is unchanged. Whether you write it or not, the row lookup goes Message → entry row → account_id either way. Skip the delegate and the path leaks into every caller. Add it and the surface looks uniform.

**Mnemonic. The macro is more accurately named `polymorphic_parent_with_creators`.** It does *not* auto-forward methods. Write the delegations on the scaffolding yourself. Choose whichever direction matches the call sites you have.

## Design Rule: Where Attributes Live

- **Parent (`entries`)**: anything you want to query, sort, filter, or index across all variants. `account_id`, `created_at`, `title`, soft-delete flags.
- **Subtype (`messages`, `comments`)**: variant-specific payload (e.g., `subject`, `body`, `parent_comment_id`).

This is what makes `Entry.where(account_id: 5).order(created_at: :desc)` a single indexed query across all variants. Polymorphic-only would require UNIONs across subtype tables.

## STI vs Delegated Type

| Choose STI when                                | Choose Delegated Type when                     |
| ---------------------------------------------- | ---------------------------------------------- |
| Variants share structure, differ in behavior   | Variants diverge structurally                  |
| Adding a column to one variant is fine for all | Variant columns would pollute the shared table |
| Cross-variant queries dominate                 | Same                                           |
| You want one class hierarchy                   | You want separate models with a shared parent  |

STI fits `User` → `Admin`, `Moderator`, `Guest` naturally (same columns, different methods).
Delegated type fits `Entry` → `Message`, `Comment`, `Post` naturally (different payload columns, shared metadata).

## N+1 Gotcha

Rendering a mixed collection fires one query per entry to load its subtype:

```ruby
# bad — N+1
current_account.entries.limit(50).each { |e| render e.entryable }

# good — one query per subtype table
current_account.entries.includes(:entryable).limit(50)
```

`includes(:entryable)` groups by `entryable_type` and issues one query per subtype table, regardless of row count.

**Limit of polymorphic includes.** `includes(entryable: :author)` only works if *every* variant has an `author` association with that exact name. If variants have different nested associations, you have to preload per-type (separate queries per variant) or narrow the collection to a single type first (`entries.messages.includes(entryable: :author)`).

**Narrow-then-preload: only loading one variant's payload.** When you only care about one variant, filter with the type scope first. Then preload:

```ruby
# Only message-typed entries, with their Message payloads — 2 queries, no comments table touched
account.entries.messages.includes(:entryable)
# SELECT * FROM entries WHERE account_id = ? AND entryable_type = 'Message'
# SELECT * FROM messages WHERE id IN (...)
```

Compare to the unfiltered preload, which fires one query per *distinct* `entryable_type` in the result (entries + messages + comments).

**Scope vs association. Why `includes(:messages)` doesn't work.** `Entry.messages` is a class-level **scope** generated by `delegated_type`. It's a SQL filter (`where entryable_type = 'Message'`). `includes` only accepts **association names** declared via `belongs_to` / `has_many` / `has_one`. `:messages` is neither. It's a relation factory. Passing it to `includes` raises `AssociationNotFoundError`. The polymorphic association name on `Entry` is `:entryable` (singular). That's what `includes` consumes. The type scopes are for filtering the relation itself.

## Related Concepts

None yet in this wiki. Polymorphic associations and STI are natural neighbors worth adding separately.
