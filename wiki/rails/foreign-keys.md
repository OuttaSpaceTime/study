---
title: Foreign keys
aliases:
- foreign key
- foreign key constraint
- add_foreign_key
- on_delete
- referential integrity
tags:
- rails
- postgres
- database
- migrations
created: '2026-06-10'
updated: '2026-06-10'
source_skill: study-walkthrough
flashcard_ids:
- cmq8hw4vw0000j70mqz3fb339
- cmq8hw75w0001j70mf0kbcv8t
- cmq8hwa0t0002j70mfor6qqf7
probe_sections:
- Two layers - DB constraint vs app validation
- Which row the constraint blocks from deletion
- on_delete vs dependent and which side effects decide
- The four referential actions and the real default
- RESTRICT vs NO ACTION is only about deferrability
- A foreign key does not create an index
last_probed:
- Which row the constraint blocks from deletion
- RESTRICT vs NO ACTION is only about deferrability
- A foreign key does not create an index
- Two layers - DB constraint vs app validation
- on_delete vs dependent and which side effects decide
- The four referential actions and the real default
depth: 1
next_review: '2026-06-18'
review_interval: 4
---

# Foreign keys

A foreign key is a database constraint that says "this column must point at a real row in another table." Rails has its own parallel machinery (`belongs_to` validations, `dependent:`) that looks like it does the same job. It does not. The two live at different layers and catch different failures, and knowing which is which is the whole game.

## TL;DR

- Enforce integrity at the **database** with a foreign key. It fires on every write, including the ones that skip Rails.
- Validate in the **app** (`belongs_to`, `validates ... presence: true`) for fast user-facing error messages, not as your real guarantee.
- For cascading deletes, pick the layer by the child's **side effects**: callbacks to run means Rails `dependent:`, pure data means DB `on_delete: :cascade`. Using both is the common belt-and-suspenders setup.
- A foreign key does **not** create an index on the referencing column in Postgres. You must add it yourself, or parent deletes seq-scan the child table.

## Two layers - DB constraint vs app validation

The Rails validation is Ruby code that only runs when a write goes through ActiveRecord's validation path. The foreign key is enforced by Postgres on every write, no matter how the row got there.

These four lines all set `event_id`, but only the first runs the Rails presence validation:

```ruby
item.update(event_id: 999)                    # validated, blocked if 999 missing
item.update_column(:event_id, 999)            # skips validation, hits DB directly
Item.insert_all([{ event_id: 999 }])          # skips validation
Item.where(id: 1).update_all(event_id: 999)   # skips validation
```

`update_column`, `insert_all`, and `update_all` are deliberate "skip callbacks and validations" tools. Add a raw `psql` session, a data migration, or a second app on the same database, and the Rails guard is bypassed entirely. The foreign key is the only thing standing behind all of those paths. So the rule. Validate in the app for UX, enforce in the DB for truth.

## Which row the constraint blocks from deletion

The constraint lives as a column on the **referencing (child)** table and guarantees that column points at a live row in the **referenced (parent)** table. That asymmetry decides which delete is blocked, and it is the part people most often get backwards.

- Deleting the **parent** (the pointed-at row) while children still reference it is what `on_delete` governs. It is blocked under `NO ACTION` / `RESTRICT`, or cascaded / nullified.
- Deleting the **child** (the row holding the foreign key column) is always allowed. It just drops a reference and orphans nothing.

So with a foreign key on `items.event_id` referencing `events`, deleting an `event` that still has items is blocked, while deleting an `item` is always fine. Flip the schema so `events` holds an `item_id` referencing `items` and it reverses, so now deleting the referenced `item` is blocked, and deleting the `event` is free.

The trap is reading "importance" into it. The rule is purely structural. The foreign key protects the pointed-at row from vanishing, so it constrains deletion of whatever is **referenced**, never the row that holds the column.

## on_delete vs dependent and which side effects decide

Both of these make "delete a parent, its children go too" happen:

```ruby
# Rails association, runs in Ruby
class Event < ApplicationRecord
  has_many :items, dependent: :destroy
end

# DB constraint, runs in Postgres
add_foreign_key :items, :events, on_delete: :cascade
```

They are not interchangeable:

| | `on_delete: :cascade` (DB) | `dependent: :destroy` (Rails) |
| --- | --- | --- |
| Runs in | Postgres | Ruby |
| Callbacks | bypassed entirely | `before_destroy` / `after_destroy` run per row |
| Further dependent associations | only along edges that also have a DB cascade | followed in Ruby |
| Speed | one SQL statement | one query per row |
| Survives `event.delete` / raw SQL | yes | no, only `destroy` triggers it |

The deciding property is whether the child has **side effects**. If `Item` has `after_destroy :purge_from_search_index` or its own `dependent: :destroy` attachments, a blind DB cascade deletes the rows and the search index goes stale and the attachments orphan. If the child is pure data, the DB cascade is enough and far faster.

Using **both** is common and composes cleanly. Rails always acts first (`dependent: :destroy` deletes children, running callbacks), and the foreign key is the integrity net that catches every delete path Rails cannot see.

## The four referential actions and the real default

`on_delete` (and `on_update`) chooses what Postgres does when the parent is deleted:

- `:cascade` - delete the referencing child rows too
- `:nullify` - set the child's foreign key column to NULL (the column must be nullable)
- `:restrict` - block the parent delete while any child references it
- `NO ACTION` - also block the parent delete, **this is the default**

Rails' `on_delete:` accepts exactly three symbols, `:cascade`, `:nullify`, `:restrict`. There is no `:no_action` symbol. You get `NO ACTION` by **omitting** `on_delete` entirely. Rails then writes no `ON DELETE` clause, and Postgres falls back to its own default of `NO ACTION`.

> [Note] A common reference claim is that the default is `RESTRICT`. It is not. With no clause emitted, Postgres uses `NO ACTION`. They look identical in everyday use, which is why the myth survives.

## RESTRICT vs NO ACTION is only about deferrability

`RESTRICT` and `NO ACTION` both block a parent delete while children exist. In the everyday case they are indistinguishable. There are two independent switches on a constraint:

| Switch | Options | Controls |
| --- | --- | --- |
| Action | `CASCADE` / `SET NULL` / `RESTRICT` / `NO ACTION` | what happens on parent delete |
| Timing | `NOT DEFERRABLE` (default) / `DEFERRABLE INITIALLY DEFERRED` / `... IMMEDIATE` | when the check runs |

The timing default is always `NOT DEFERRABLE`, for every action. So `NO ACTION` is **not** "deferred by default." The actual relationship. `NO ACTION` is the only blocking action that is **eligible** to be deferred to `COMMIT`. `RESTRICT` always fires immediately at each statement and can never be deferred, even on a `DEFERRABLE` constraint.

This is why a parent-first delete inside one transaction only survives under `NO ACTION` plus deferral:

```sql
BEGIN;
DELETE FROM events WHERE id = 42;        -- orphan exists right now
DELETE FROM items  WHERE event_id = 42;  -- orphan gone
COMMIT;                                   -- deferred check runs here, clean
```

In Rails it takes two ingredients. A plain transaction is not enough, the constraint must be declared deferrable at creation time:

```ruby
# 1. migration
add_foreign_key :items, :events, deferrable: :deferred

# 2. then the transaction defers automatically to COMMIT
Event.transaction do
  event.destroy
  # ...children cleaned up in the wrong order...
end
```

`deferrable:` takes `:deferred` (`DEFERRABLE INITIALLY DEFERRED`, postponed to COMMIT automatically), `:immediate` or `true` (`DEFERRABLE INITIALLY IMMEDIATE`, capable but you opt in per transaction with `SET CONSTRAINTS ALL DEFERRED`), or `false` (the default, not deferrable at all). Pairing `on_delete: :restrict` with `deferrable: :deferred` does nothing, because `RESTRICT` ignores deferral.

## A foreign key does not create an index

In Postgres, declaring a foreign key does **not** create an index on the referencing column. The referenced side (`events.id`) is indexed because it is the primary key, but the referencing side (`items.event_id`) is on you.

This is a performance landmine, because the foreign key makes the **parent's** deletes and updates slow, not just your own queries. Every time you delete or update an `events` row, Postgres scans `items` to enforce the constraint. With no index that is a full sequential scan of `items` on every event delete, holding locks the whole time.

Rails gives you a shortcut that does the right thing, and a low-level form that does not:

```ruby
add_reference :items, :event, foreign_key: true  # column + index + FK constraint
add_foreign_key :items, :events                  # FK constraint only, column must exist, no index
```

So when you use bare `add_foreign_key`, remember the second line:

```ruby
add_foreign_key :items, :events
add_index :items, :event_id
```

On a large existing table, adding the foreign key itself scans every row to validate it and holds a lock. Use `validate: false` to add the constraint without the initial scan (enforced on new writes only), then `validate_foreign_key` later when you can afford the scan:

```ruby
add_foreign_key :line_items, :orders, validate: false
# in a later migration
validate_foreign_key :line_items, :orders
```

## Related Concepts

- [[sql/nullable-columns]]: nullable foreign keys and what `on_delete: :nullify` needs from the column
- [[rails/activerecord-preloading]]: the same "Rails loads each row in Ruby" cost that makes `dependent: :destroy` slow

## References

- [PostgreSQL docs, Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html): official reference for referential actions, deferrability, and the no-auto-index behavior
- [Rails Guides, Active Record Migrations](https://guides.rubyonrails.org/active_record_migrations.html): `add_foreign_key`, `add_reference`, `foreign_key: true`
- [Rails API, SchemaStatements](https://api.rubyonrails.org/classes/ActiveRecord/ConnectionAdapters/SchemaStatements.html): exact `add_foreign_key` options including `on_delete`, `validate`, `deferrable`
