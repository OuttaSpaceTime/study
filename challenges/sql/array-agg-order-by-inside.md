---
wiki: sql/array-agg
section: Ordering is non-deterministic by default
kind: write-code
env: pg
questions:
- What can silently change the array order when array_agg has no ORDER BY?
- Where does the ORDER BY go, and how does it relate to an outer ORDER BY on the query?
created: 2026-07-03
---

## Brief

Without an explicit ORDER BY the array reflects whatever order the executor emitted, which can flip with plan changes. Make the order deterministic so the earliest created_at comes first.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, product text, created_at date);
INSERT INTO orders (product, created_at) VALUES
  ('pear', '2026-01-02'),
  ('apple', '2026-01-01'),
  ('fig', '2026-01-03');
```

## Stub

```sql
-- TODO: make the array order deterministic, oldest created_at first
SELECT array_agg(product) FROM orders;
```

## Solution

```sql
SELECT array_agg(product ORDER BY created_at) FROM orders;
```

## Expected Output

```
    array_agg     
------------------
 {apple,pear,fig}
(1 row)

```
