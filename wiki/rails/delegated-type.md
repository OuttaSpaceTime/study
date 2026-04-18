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
updated: '2026-04-17'
source_skill: study-walkthrough
depth: 1
last_deepened: '2026-04-17'
next_review: '2026-04-20'
review_interval: 3
probe_sections:
- The Problem It Solves
- Schema Shape
- The Declaration
- Direction of Delegation
- 'Design Rule: Where Attributes Live'
- STI vs Delegated Type
- N+1 Gotcha
last_probed: []
---

# Delegated Type

A Rails pattern for modeling heterogeneous subtypes that **share some fields but have different payload schemas**. A "superclass" table holds the shared attributes; each variant lives in its own table. The parent row points to the variant row via a polymorphic association, and variants delegate shared-attribute reads *back up* to the parent.

It's the answer to "STI would work but the variants diverge too much in schema" and "polymorphic associations alone make cross-type queries awkward."

## The Problem It Solves

Modeling `Entry` with variants `Message`, `Comment`, `Post`:

- **Fat table** (one table, nullable columns per variant) — NULL-heavy, no schema discipline.
- **STI** (`type` column, one table) — variants must share the schema; adding variant-specific columns bloats the table.
- **Polymorphic only** — flexible, but shared attributes (`account_id`, `created_at`) scatter across subtype tables, so "all entries this week across types" requires UNIONs.
- **Delegated type** — shared attrs on the parent, variant attrs on the subtype. One indexable, queryable parent table plus clean per-variant tables.

## Schema Shape

```
accounts:  id, name
entries:   id, account_id, entryable_type, entryable_id, created_at
messages:  id, subject, body
comments:  id, content
```

The `entries` row holds:
- `entryable_id` — the row id in the subtype table
- `entryable_type` — string like `"Message"` / `"Comment"` telling Rails which table

Both are needed: an id alone is ambiguous across multiple subtype tables.

## The Declaration

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
4. Creators: `Entry.create_with_message!(subject: "hi", body: "...")` — creates the subtype row *and* the parent `Entry` row atomically.

## Direction of Delegation

Counterintuitive: `delegated_type` does **not** auto-delegate methods from the parent down to the subtype. `entry.subject` raises `NoMethodError` unless you write your own `delegate :subject, to: :entryable` on `Entry`.

The "delegated" in the name refers to the **inverse direction**: each subtype delegates *up* to the parent for shared attributes. `account_id` lives on `entries`, so:

```ruby
message.account          # works via delegate :account, to: :entry
message.entry.account    # same thing, explicit
```

Without the delegate, callers would have to walk through `.entry` manually. The delegate is pure ergonomics — the data path is unchanged.

## Design Rule: Where Attributes Live

- **Parent (`entries`)** — anything you want to query, sort, filter, or index across all variants. `account_id`, `created_at`, `title`, soft-delete flags.
- **Subtype (`messages`, `comments`)** — variant-specific payload. `subject`, `body`, `parent_comment_id`.

This is what makes `Entry.where(account_id: 5).order(created_at: :desc)` a single indexed query across all variants. Polymorphic-only would require UNIONs across subtype tables.

## STI vs Delegated Type

| Choose STI when | Choose Delegated Type when |
|---|---|
| Variants share structure, differ in behavior | Variants diverge structurally |
| Adding a column to one variant is fine for all | Variant columns would pollute the shared table |
| Cross-variant queries dominate | Same |
| You want one class hierarchy | You want separate models with a shared parent |

Classic STI fit: `User` → `Admin`, `Moderator`, `Guest` (same columns, different methods).
Classic delegated-type fit: `Entry` → `Message`, `Comment`, `Post` (different payload columns, shared metadata).

## N+1 Gotcha

Rendering a mixed collection fires one query per entry to load its subtype:

```ruby
# bad — N+1
current_account.entries.limit(50).each { |e| render e.entryable }

# good — one query per subtype table
current_account.entries.includes(:entryable).limit(50)
```

`includes(:entryable)` groups by `entryable_type` and issues one query per subtype table, regardless of row count.

**Limit of polymorphic includes:** `includes(entryable: :author)` only works if *every* variant has an `author` association with that exact name. If variants have different nested associations, you have to preload per-type (separate queries per variant) or narrow the collection to a single type first (`entries.messages.includes(entryable: :author)`).

## Related Concepts

None yet in this wiki — polymorphic associations and STI are natural neighbors worth adding separately.
