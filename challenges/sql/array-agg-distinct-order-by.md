---
wiki: sql/array-agg
section: DISTINCT + ORDER BY must share the expression
kind: write-code
env: pg
questions:
- Why must the ORDER BY expression match the DISTINCT expression inside an aggregate?
- How would you get distinct products ordered by created_at anyway?
created: 2026-07-03
---

## Brief

This query errors because the sort key differs from the dedup key. Fix the ORDER BY so the query runs.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, product text, created_at date);
INSERT INTO orders (product, created_at) VALUES
  ('pear', '2026-01-01'),
  ('apple', '2026-01-02'),
  ('pear', '2026-01-03');
```

## Stub

```sql
-- TODO: this errors; fix the ORDER BY so it works with DISTINCT
SELECT array_agg(DISTINCT product ORDER BY created_at) FROM orders;
```

## Solution

```sql
SELECT array_agg(DISTINCT product ORDER BY product) FROM orders;
```

## Expected Output

```
  array_agg   
--------------
 {apple,pear}
(1 row)

```
