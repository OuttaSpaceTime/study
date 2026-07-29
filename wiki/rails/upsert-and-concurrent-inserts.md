---
title: Upsert and concurrent inserts
aliases:
- ON CONFLICT
- upsert
- insert_all
- upsert_all
- find_or_create_by race
- RecordNotUnique
- excluded pseudo-table
tags:
- rails
- postgres
- database
- concurrency
created: '2026-06-14'
updated: '2026-06-14'
source_skill: study-walkthrough
flashcard_ids: []
review_interval: 20
next_review: '2026-07-24'
---

# Upsert and concurrent inserts

How PostgreSQL handles two background jobs racing to insert the same row, what `ON CONFLICT` lets you do about it, and how Rails `create!` / `insert_all` / `upsert_all` map onto that machinery. The through-line. Under concurrency, the database constraint is the only real integrity guarantee, and upsert is how you handle the conflict without raising.

## TL;DR

- Two jobs insert the same key. The second one **blocks** until the first commits or rolls back. If the first commits, the second fails with a unique violation. If the first rolls back, the second succeeds.
- A unique index does **not** prevent the race. It converts a *silent duplicate* into a *catchable error* (`23505` / `ActiveRecord::RecordNotUnique`).
- `ON CONFLICT` hands the database an instruction (`DO NOTHING` or `DO UPDATE`) instead of letting the insert raise. `DO UPDATE` is the "upsert".
- `ON CONFLICT` only covers the one **arbiter** index you name. A collision on any other unique constraint still raises.
- Rails: `create!` / `insert_all!` raise on conflict, `insert_all` does `DO NOTHING`, `upsert_all` does `DO UPDATE`.
- `insert_all` / `upsert_all` skip validations and callbacks. DB constraints, not Ruby validations, are the guarantee.

## The Race Between Two Concurrent Inserts

Two jobs run the identical statement a millisecond apart against a table with a unique index on `(user_id, event_key)`:

```ruby
# Job A, then job B a moment later
Event.create!(user_id: 7, event_key: "signup")
```

Job A's `INSERT` runs first but its transaction has **not committed yet**. Job B fires the same `INSERT` and **blocks**. Per the PostgreSQL docs, "if a conflicting row has been inserted by an as-yet-uncommitted transaction, the would-be inserter must wait to see if that transaction commits" ([index uniqueness checks](https://www.postgresql.org/docs/current/index-unique-checks.html)).

Blocking is not the same as failing. B's outcome is decided by what A does next:

- **A commits.** Its row is now permanent and visible, so B's insert violates the index and fails.
- **A rolls back.** The conflicting row never persisted, so B's wait ends and B inserts successfully.

When B does fail, PostgreSQL raises `SQLSTATE 23505` (`unique_violation`), which ActiveRecord wraps as `ActiveRecord::RecordNotUnique`. The bang matters. `create!` raises it, plain `create` would hand back an unsaved object instead.

The key mental model for the rest of this page. **A constraint does not stop the race from happening. It makes the race's outcome safe and well-defined** instead of silently writing two rows.

## ON CONFLICT DO NOTHING vs DO UPDATE

`ON CONFLICT` is how you tell PostgreSQL what to do *instead of* raising on a conflict. There are exactly two actions.

```sql
-- skip the conflicting row, insert nothing for it
INSERT INTO events (user_id, event_key)
VALUES (7, 'signup')
ON CONFLICT (user_id, event_key) DO NOTHING;

-- update the existing row instead (this is the "upsert")
INSERT INTO event_counts (user_id, event_key, count)
VALUES (7, 'signup', 5)
ON CONFLICT (user_id, event_key)
DO UPDATE SET count = event_counts.count + excluded.count;
```

**The `excluded` pseudo-table.** A `DO UPDATE` usually needs *both* rows, the one already in the table and the one you tried to insert. The existing row is referenced by the table name (`event_counts.count`). The rejected, proposed row is exposed as the pseudo-table `excluded` (`excluded.count`). So `event_counts.count + excluded.count` is "existing value plus the incoming value", which is what makes deterministic counter increments and idempotent recovery possible. `excluded` reflects the effects of any `BEFORE INSERT` triggers ([INSERT docs](https://www.postgresql.org/docs/current/sql-insert.html)).

**The arbiter index is required.** `ON CONFLICT (user_id, event_key)` is not a free-form hint. It points at a real unique (or exclusion) index, called the arbiter. Two failure shapes to keep distinct:

- **No matching unique index for the named target at all.** The *statement itself* errors with "there is no unique or exclusion constraint matching the ON CONFLICT specification". This is a query error, not a row collision.
- **A matching arbiter exists, but the collision lands on a different unique constraint.** `ON CONFLICT` only covers the arbiter you named, so the other violation raises normally (`23505`). Upsert is not a blanket "ignore all duplicates".

Two more rules worth knowing. `DO UPDATE` **requires** a `conflict_target`, while `DO NOTHING` may omit it (then any usable constraint applies). And a *partial* unique index can only be the arbiter if the statement's predicate matches or implies the index `WHERE`. See [[sql/nullable-columns]] for partial unique indexes.

## RETURNING Returns Only Touched Rows

`RETURNING` gives back only the rows actually **inserted or updated**, not the rows your statement skipped.

```ruby
ids = Event.insert_all(
  [
    { user_id: 7, event_key: "signup" },   # already exists
    { user_id: 7, event_key: "login"  },   # new
    { user_id: 7, event_key: "logout" },   # new
  ],
  returning: [:id]
)
# ids has 2 rows, not 3
```

Because `insert_all` emits `ON CONFLICT DO NOTHING`, the conflicting `signup` row is skipped and so is absent from `RETURNING`. **Never assume `returning` gives one row per input row.** If you need the IDs of the skipped rows too, re-`SELECT` them by their keys. `upsert_all` (which does `DO UPDATE`) does not have this hole in the same way, because conflicting rows are touched and therefore returned.

## Rails Create!, insert_all, insert_all!, upsert_all

Each Rails write maps onto a specific SQL conflict behavior:

| Method | SQL emitted | On a duplicate |
| --- | --- | --- |
| `create!` / `save!` | plain `INSERT` | raises `RecordNotUnique` |
| `insert_all` | `INSERT ... ON CONFLICT DO NOTHING` | silently skips the row |
| `insert_all!` | plain `INSERT` (no conflict clause) | raises `RecordNotUnique`, inserts nothing |
| `upsert_all` | `INSERT ... ON CONFLICT DO UPDATE` | updates the existing row |

The bang follows the usual Rails convention (raise vs not), with one twist. The non-bang `insert_all` does not raise *and* does not update. It skips.

Options on the bulk methods:

- `unique_by:` picks which unique index is the arbiter. Required when more than one unique index could match, and it must reference an existing index (with the correct `WHERE` for a partial index).
- `on_duplicate:` is the `DO UPDATE` clause for `upsert_all` (defaults to updating all supplied columns).
- `returning:` controls the `RETURNING` columns (PostgreSQL and SQLite only; defaults to the primary key, `false` to omit).
- `record_timestamps:` Since Rails 7.0, `created_at` / `updated_at` are set automatically by default for these methods. Before 7.0 you had to pass them yourself.

## Bulk Methods Bypass Validations and Callbacks

`insert_all` and `upsert_all` are fast because they talk straight to the database with one round-trip and no per-row model instantiation. That speed comes from skipping the model layer entirely.

```ruby
class Event < ApplicationRecord
  validates :event_key, presence: true
  before_create { self.normalized_key = event_key.downcase }
end

Event.upsert_all([{ user_id: 7, event_key: "" }])
```

The `presence` validation does **not** fire, the `before_create` callback does **not** run, and the blank `event_key` lands in the table with `normalized_key` unset. Values still go through type casting and serialization, but nothing in your model code runs.

This is the thesis of the whole topic. Once you bypass the ORM, application-level guarantees evaporate, so **integrity has to live at the database level** through unique indexes, `NOT NULL`, check and foreign-key constraints (see [[rails/foreign-keys]]). A Ruby validation is a UX nicety; the constraint is the guarantee.

## find_or_create_by Is not Atomic

The idiom people actually write looks safe but is not:

```ruby
Event.find_or_create_by(user_id: 7, event_key: "signup")
# SELECT ... WHERE user_id = 7 AND event_key = 'signup' LIMIT 1
# (if none) INSERT INTO events ...
```

It is **check-then-act**, a `SELECT` followed by an `INSERT`. Under the A/B race, both jobs `SELECT`, both find nothing, and both `INSERT`.

- **With no unique index**, both inserts succeed and you get two rows. Silent corruption.
- **With a unique index**, the race still happens, but its outcome is now safe: the losing job's insert raises `RecordNotUnique` instead of duplicating.

Once the failure is catchable you have two clean responses:

1. **Rescue and retry.** `rescue ActiveRecord::RecordNotUnique` then re-run the `find`. Keeps validations and callbacks, at the cost of a retry path.
2. **Upsert.** Replace the check-then-act with a single atomic `upsert_all` (or `INSERT ... ON CONFLICT`). No exception, no retry, but it skips validations and callbacks.

Both are only *possible* because the constraint exists.

## Tradeoffs and Gotchas

- **"No locks" is imprecise (contested).** Practitioner write-ups sometimes sell upsert as lock-free ([coorasse](https://coorasse.com/blog/from-three-queries-to-one-with-upsert/)). The accurate claim is that there is no *application-level* lock and no retry loop. PostgreSQL still briefly waits on the uncommitted conflicting row at the row level ([index uniqueness checks](https://www.postgresql.org/docs/current/index-unique-checks.html)).
- **Idempotent jobs via a unique key (consensus).** At-least-once delivery means a job *will* sometimes re-run. A unique constraint on an idempotency key plus `upsert` or `DO NOTHING` is atomic at the database, unlike a Redis guard clause, which has its own check-then-act race.
- **Validation/callback skip is a real integrity risk (consensus).** Rails docs and practitioners ([Nunemaker](https://www.johnnunemaker.com/rails-insert_all-and-upsert_all/)) treat the bypass as load-bearing, not a footnote. Some posts downplay it; weight the warning.
- **Sequence and primary-key gaps are normal (note).** A skipped or failed insert still consumes the sequence value, so IDs are non-monotonic with gaps. Do not rely on contiguous IDs.
- **Batch ordering avoids deadlocks (consensus).** When upserting batches, order rows by key so concurrent batches lock in the same order. Multiple unique indexes can also make arbiter selection ambiguous, so name it with `unique_by`.

## Related Concepts

- [[sql/nullable-columns]]: partial unique indexes (a partial arbiter needs a matching `WHERE`) and how `UNIQUE` does not constrain `NULL`s.
- [[rails/foreign-keys]]: the other DB-level integrity constraint, and the same DB-constraint-vs-app-validation split.

## References

Authoritative:

- [PostgreSQL INSERT / ON CONFLICT](https://www.postgresql.org/docs/current/sql-insert.html): conflict target inference, `excluded`, the arbiter-index requirement, `RETURNING` semantics.
- [PostgreSQL index uniqueness checks](https://www.postgresql.org/docs/current/index-unique-checks.html): the documented wait-on-uncommitted-conflict behavior.
- [Rails ActiveRecord::Persistence](https://api.rubyonrails.org/v7.1/classes/ActiveRecord/Persistence/ClassMethods.html): `insert_all` / `insert_all!` / `upsert_all` options and semantics.
- [rails/rails #43003](https://github.com/rails/rails/pull/43003): timestamps set automatically by default since Rails 7.0.

Practitioner / opinion:

- [coorasse, from three queries to one with upsert](https://coorasse.com/blog/from-three-queries-to-one-with-upsert/): the `find_or_create_by` race and upsert as the atomic replacement.
- [Nunemaker, insert_all and upsert_all](https://www.johnnunemaker.com/rails-insert_all-and-upsert_all/): real-world gotchas (timestamps, `unique_by`, the validation skip).
