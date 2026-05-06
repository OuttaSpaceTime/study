---
title: Nullable Columns
aliases:
- nullable columns
- null columns
- sql null
- nullable schema
- null in sql
tags:
- sql
- postgres
- schema-design
- data-modeling
- null
category: work
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
depth: 1
probe_sections:
- Three-valued logic is the root cause
- The NOT IN trap
- UNIQUE does not constrain NULLs
- Partial unique indexes
- Nullable foreign keys
- Migrating to NOT NULL is expensive
- When NULL is the right choice
- Sentinels masquerading as values
last_probed:
- Three-valued logic is the root cause
- The NOT IN trap
- UNIQUE does not constrain NULLs
- Partial unique indexes
- Nullable foreign keys
- Migrating to NOT NULL is expensive
- When NULL is the right choice
- Sentinels masquerading as values
---

# Nullable Columns

## TL;DR

Marking a column nullable is a one-character schema change that ripples through every query, constraint, index, and migration that touches it forever. The cost is not in writing `NULL` — it's in the asymmetric three-valued logic, the constraints that silently don't apply, and the future migration that may be impossible because the source data is gone. **Default to `NOT NULL` with a sensible default; reach for `NULL` only when the *absence* of a value is semantically distinct from any value the column could hold.**

## Three-valued logic is the root cause

SQL does not use boolean logic. It uses **three-valued logic** (3VL): every predicate evaluates to `TRUE`, `FALSE`, or `UNKNOWN`. Any comparison involving `NULL` returns `UNKNOWN` — including `NULL = NULL`. `WHERE` only keeps rows where the predicate is `TRUE`, so `UNKNOWN` rows are dropped just like `FALSE` rows.

Given a `users` table with `status ∈ {'active', 'inactive', NULL}`:

```sql
SELECT * FROM users WHERE status = 'active';   -- only active rows
SELECT * FROM users WHERE status != 'active';  -- only inactive rows; NULL rows dropped!
SELECT * FROM users WHERE status = NULL;       -- ALWAYS empty; NULL = NULL is UNKNOWN
```

The second is the trap: a developer who writes "give me everyone who isn't active" silently loses every row whose status is *unknown*. The fix is explicit:

```sql
WHERE status != 'active' OR status IS NULL
-- or, in Postgres:
WHERE status IS DISTINCT FROM 'active'
```

To test for NULL itself, use the special two-valued operators `IS NULL` / `IS NOT NULL`. Plain `=` and `!=` will never work.

`COUNT` follows the same rule: `COUNT(*)` counts rows; `COUNT(col)` counts non-NULL values in `col`. The two diverge whenever the column is nullable.

## The NOT IN trap

`NOT IN` against a nullable column is much worse than `!=`. A single NULL in the right-hand list silently empties the entire result.

```sql
SELECT * FROM users
WHERE id NOT IN (SELECT user_id FROM orders WHERE status = 'cancelled');
```

If `orders.user_id` is nullable and even one cancelled order has `user_id IS NULL`, the predicate expands to:

```
id != value_1  AND  id != value_2  AND  id != NULL
```

The last conjunct is `UNKNOWN`. `TRUE AND UNKNOWN` is `UNKNOWN`, so the whole predicate is never `TRUE`. **Result: zero rows.** Calling code that branches on "if this list is empty, do X" will silently trigger X for every user.

The fix is to use `NOT EXISTS`, which is NULL-safe by construction:

```sql
SELECT * FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM orders o
  WHERE o.status = 'cancelled' AND o.user_id = u.id
);
```

> [Heuristic] If the subquery column is nullable, `NOT IN` is a bug. Reach for `NOT EXISTS` or `LEFT JOIN ... WHERE x IS NULL`.

## UNIQUE does not constrain NULLs

A `UNIQUE` constraint on a nullable column does not prevent multiple NULLs. Two NULLs are not "equal" under SQL semantics, so the database considers them distinct:

```sql
CREATE TABLE users (id SERIAL PRIMARY KEY, email TEXT UNIQUE);
INSERT INTO users (email) VALUES (NULL);  -- ok
INSERT INTO users (email) VALUES (NULL);  -- also ok
INSERT INTO users (email) VALUES (NULL);  -- still ok
```

The same trap appears with composite uniqueness:

```sql
CREATE TABLE subscriptions (
  user_id INT,
  cancelled_at TIMESTAMP,         -- NULL = active
  UNIQUE (user_id, cancelled_at)
);
```

The intent is "at most one active subscription per user." The constraint does not enforce it: `(7, NULL)` is not equal to `(7, NULL)` because of the NULL component, so a user can accumulate any number of active rows.

> [Note] SQL Server's default is the opposite — it treats NULLs as equal in UNIQUE constraints. Postgres 15+ added `UNIQUE NULLS NOT DISTINCT` to opt into that behavior. Behavior varies by engine; do not rely on a default that is not in the standard.

## Partial unique indexes

The right tool for "unique among rows matching some predicate" is a **partial unique index** — an index built only on the subset of rows that satisfy a `WHERE` clause:

```sql
CREATE UNIQUE INDEX one_active_per_user
  ON subscriptions (user_id)
  WHERE cancelled_at IS NULL;
```

Two changes vs. a regular unique index:

1. The index stores **only rows where `cancelled_at IS NULL`** — cancelled rows are not indexed.
2. Uniqueness is enforced only among indexed rows — i.e., only among active subscriptions.

A second `INSERT (7, NULL)` collides on `user_id = 7` in the index and fails. An `INSERT (7, '2025-09-01')` is not added to the index at all (predicate is false), so it never collides.

Plain `UNIQUE` cannot scope to a subset of rows — it is all-or-nothing across the column. Partial indexes provide that scoping for both uniqueness and ordinary indexes (e.g., indexing only open tickets, only soft-undeleted rows, etc.).

> [Note] A partial index can only satisfy a query whose `WHERE` clause logically implies the index's predicate. `WHERE status = 'closed'` cannot use an index defined `WHERE status = 'open'`.

## Nullable foreign keys

A nullable FK conflates two semantically different states the database cannot distinguish:

1. **No related entity exists** (e.g., a comment with no parent — it's top-level).
2. **The related entity is unknown** (e.g., an order awaiting attribution).

Both look like NULL. The database can't tell which the schema meant, so neither can downstream code.

The FK constraint itself only fires when the value is non-NULL: `INSERT INTO posts (author_id) VALUES (NULL)` succeeds even with zero users in the system. The constraint says "if a value exists, it must reference a real row" — nothing more.

The frequent application bug is forgetting that `INNER JOIN` silently drops rows whose FK is NULL:

```sql
-- Drops every top-level comment because parent_comment_id IS NULL.
SELECT c.id, parent.author_name
FROM comments c
JOIN comments parent ON parent.id = c.parent_comment_id;
```

The fix is `LEFT JOIN`, but `LEFT JOIN` then yields NULL columns for the unmatched side, and any subsequent `WHERE parent.author_name = ...` falls back into the 3VL trap from the first section.

If "no relation" is rare or only valid in a specific state, prefer modeling it differently — a separate table, an `is_*` flag, or a sentinel "system user" — rather than a nullable FK that has to be handled correctly at every read site.

## Migrating to NOT NULL is expensive

Tightening a nullable column to `NOT NULL` later is three stacked problems, not one:

1. **What value to use for existing NULLs?** Often there is no defensible default. `0`, `''`, `'unknown'` are all lies. The right answer may require reaching into other tables or external systems — and the source signal (HTTP referrer, campaign param, client metadata) may no longer exist.
2. **The backfill is a long-running write.** On a large table, `UPDATE ... WHERE col IS NULL` runs for tens of minutes, holds row locks, generates large WAL/binlog volume, and replicates slowly. Done naively it stalls production.
3. **`ALTER TABLE ... SET NOT NULL` is itself locking.** In Postgres < 12 it takes ACCESS EXCLUSIVE and scans the table while holding it. Postgres 12+ can validate against an existing `CHECK (col IS NOT NULL) NOT VALID` to skip the rescan.

The standard online pattern for adding `NOT NULL` to a populated column:

```sql
-- 1. Application starts writing the column on every new row (no new NULLs created).
-- 2. Backfill in batches:
UPDATE users SET status = 'unknown' WHERE id BETWEEN 1 AND 10000 AND status IS NULL;
-- ... repeat in chunks until done.

-- 3. Add the constraint without a rescan:
ALTER TABLE users ADD CONSTRAINT users_status_not_null
  CHECK (status IS NOT NULL) NOT VALID;

-- 4. Validate (weaker lock, but still scans the table once):
ALTER TABLE users VALIDATE CONSTRAINT users_status_not_null;

-- 5. (Postgres 12+) Convert to a real NOT NULL using the validated check, no rescan:
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

Compare to the easy case: a `NOT NULL` column with a default added on day one has none of this work. The cost of `NULL` is mostly paid later, by the team trying to enforce a real constraint after the table has 50M rows and the source data is gone.

## When NULL is the right choice

The danger story is one-sided. NULL is the correct modeling choice when **the absence of a value is semantically distinct from any value the column could hold**:

- **Genuine "unknown" or "not yet measured."** A `weight_kg` for hospital patients where some have not been weighed. Using `0` would corrupt `AVG(weight_kg)`; NULL correctly excludes the row.
- **"Not applicable" intrinsic to the row.** A `parent_comment_id` on a top-level comment really has no parent — there is no value that would be meaningful, and inventing a fake top-level row is worse than NULL.
- **Soft delete timestamps.** `deleted_at IS NULL` for active rows, a timestamp for deleted ones. Each timestamp value carries when-was-it-deleted information; NULL carries the orthogonal still-active fact.

The decision question:

> *Is the absence of a value semantically meaningful and distinct from any value the column could hold?*

- Yes → NULL is appropriate.
- No (you are reaching for NULL because you could not think of a default) → use `NOT NULL` with a default, a separate table, or a richer enum.

## Sentinels masquerading as values

A common reflex after reading the above is "always `NOT NULL`, use a sentinel." This is worse than NULL when the sentinel looks like real data:

- `email = ''` matches `WHERE email = ''` and compares equal to itself — it pollutes JOINs, equality checks, and uniqueness constraints exactly when you do not want it to.
- `weight_kg = 0` is included in `AVG`, `SUM`, `MIN` — corrupting aggregates the way NULL does not.
- `signup_date = '1970-01-01'` is a sortable date that appears in date-range filters as if it were a real signup.

The honest representation of "absent" is `NULL` plus the discipline to handle 3VL at every read site. The dishonest representation is a sentinel that is treated as a real value by every operator and aggregate. Choose based on whether the column is read-heavy with aggregates (lean toward `NOT NULL` with a chosen default that respects the math) or whether downstream code must distinguish absent from any value (lean toward `NULL`).

## Related Concepts

- [[sql/array-agg]] — aggregates and NULL handling: `array_agg` includes NULLs by default (unlike `SUM`/`AVG`); same 3VL theme applied to set-collecting aggregates.
