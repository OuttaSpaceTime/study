---
title: array_agg
aliases:
- array_agg
- postgres array_agg
- sql array aggregate
tags:
- sql
- postgres
- aggregate
created: '2026-04-17'
updated: '2026-04-17'
source_skill: study-walkthrough
depth: 1
probe_sections:
- What array_agg collects and the implicit single-group rule
- No GROUP BY means one implicit group
- Ordering is non-deterministic by default
- NULLs are included by default
- Empty input returns NULL, not {}
- DISTINCT + ORDER BY must share the expression
- array_agg vs jsonb_agg
- Canonical shape for "safe" usage
last_probed:
- NULLs are included by default
- Empty input returns NULL, not {}
- DISTINCT + ORDER BY must share the expression
- array_agg vs jsonb_agg
- Canonical shape for "safe" usage
- What array_agg collects and the implicit single-group rule
- No GROUP BY means one implicit group
- Ordering is non-deterministic by default
review_interval: 3
next_review: '2026-05-13'
flashcard_ids: []
---

# array_agg

## TL;DR

`array_agg(col)` is the aggregate function that collapses a group of rows into an **array of values** instead of a scalar. Where `COUNT(col)` gives *how many*, `array_agg(col)` gives *which ones*. Without discarding the individual values.

```sql
SELECT user_id, array_agg(product) AS products
FROM orders
GROUP BY user_id;

--  user_id | products
-- ---------+----------------
--  1       | {apple, pear}
--  2       | {apple}
```

## What array_agg collects and the implicit single-group rule

Aggregates collapse N rows into 1 row per group. `SUM`, `AVG`, `COUNT` collapse to a scalar. `array_agg` collapses to a **collection**. It is the aggregate that *doesn't throw away the individual values*.

This lets a single query return both "the group" and "its members" without a second round-trip or client-side grouping.

## No GROUP BY means one implicit group

Like every aggregate, `array_agg` without `GROUP BY` treats the whole (possibly filtered) table as a single group and returns one row:

```sql
SELECT array_agg(product) FROM orders;
-- => {apple, pear, apple}    -- one array containing every row's product
```

## Ordering is non-deterministic by default

The array reflects whatever order the executor happened to emit rows in. That order can shift with query plan changes (new index, updated stats), parallel scan chunking, version upgrades, or primary vs. replica. So an ordering that looks fine locally can flip in production.

If any consumer cares about the order (cache keys, snapshot tests, `arr[1]` as "the first"), make it explicit with `ORDER BY` **inside** the aggregate:

```sql
array_agg(product ORDER BY created_at)
```

This ordering is per-aggregate and independent of any outer `ORDER BY` on the query.

## NULLs are included by default

Unlike `SUM`/`AVG`, which ignore NULLs, `array_agg` includes them:

```sql
SELECT array_agg(product) FROM orders;  -- => {apple, pear, apple, NULL}
```

Filter them out with `FILTER`:

```sql
array_agg(product) FILTER (WHERE product IS NOT NULL)
```

## Empty input returns NULL, not {}

> [Warning] When an aggregate receives zero input rows (empty group, or everything filtered out), it returns **`NULL`**. Not an empty array. `COUNT` is the only aggregate that returns `0` on empty input.

This matters because consumer code that does `result.length` or iterates will behave differently on `NULL` vs. `{}`. Defaulting to empty is usually the safer contract:

```sql
COALESCE(
  array_agg(product) FILTER (WHERE product IS NOT NULL),
  ARRAY[]::text[]
)
```

The explicit `::text[]` cast is required. Postgres cannot infer the element type of a bare `ARRAY[]`.

## DISTINCT + ORDER BY must share the expression

When combining `DISTINCT` and `ORDER BY` inside `array_agg`, the sort expression must match the distinct expression:

```sql
-- good
array_agg(DISTINCT product ORDER BY product)

-- bad — errors
array_agg(DISTINCT product ORDER BY created_at)
```

Intuition. With `DISTINCT`, the aggregate dedupes first; the dedup key has to equal the sort key for the result to be well-defined. To order distinct values by a *different* column, dedupe upstream with `SELECT DISTINCT ON (...)` in a subquery and aggregate over that.

## array_agg vs jsonb_agg

Both collect rows into a collection. The choice is about **shape of the elements**:

| | `array_agg` | `jsonb_agg` |
|---|---|---|
| elements | one scalar type per array | heterogeneous / structured |
| operators | `ANY`, `@>`, `unnest`, GIN indexes | JSON path operators, `->`, `->>` |
| overhead | minimal | JSON encoding |
| use case | collections of same-kind things | collections of records |

```sql
-- same-kind scalars → array_agg
array_agg(product)

-- structured records → jsonb_agg
jsonb_agg(jsonb_build_object('product', product, 'at', created_at))
```

## Canonical shape for "safe" usage

When order, NULLs, duplicates, and empty input all matter:

```sql
SELECT user_id,
       COALESCE(
         array_agg(DISTINCT product ORDER BY product)
           FILTER (WHERE product IS NOT NULL),
         ARRAY[]::text[]
       ) AS products
FROM orders
GROUP BY user_id;
```

## Related Concepts

- [[rails/activerecord-pick]]: another "collapse many rows into one value in a single round-trip" pattern, at the ActiveRecord layer
