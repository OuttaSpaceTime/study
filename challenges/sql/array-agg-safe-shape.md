---
wiki: sql/array-agg
section: Canonical shape for "safe" usage
kind: write-code
env: pg
questions:
- Why is the explicit ARRAY[]::text[] cast required in the fallback?
- Which part of the canonical shape handles order, NULLs, duplicates, and empty input respectively?
created: 2026-07-03
---

## Brief

User 2 only has NULL products, so the filtered aggregate yields NULL for that group. Complete the query so such groups return an empty array instead.

## Setup

```sql
CREATE TABLE orders (user_id int, product text);
INSERT INTO orders VALUES
  (1, 'pear'), (1, 'apple'), (1, 'apple'), (1, NULL),
  (2, NULL);
```

## Stub

```sql
SELECT user_id,
       -- TODO: make groups with no non-NULL products return {} instead of NULL
       array_agg(DISTINCT product ORDER BY product)
         FILTER (WHERE product IS NOT NULL) AS products
FROM orders
GROUP BY user_id
ORDER BY user_id;
```

## Solution

```sql
SELECT user_id,
       COALESCE(
         array_agg(DISTINCT product ORDER BY product)
           FILTER (WHERE product IS NOT NULL),
         ARRAY[]::text[]
       ) AS products
FROM orders
GROUP BY user_id
ORDER BY user_id;
```

## Expected Output

```
 user_id |   products   
---------+--------------
       1 | {apple,pear}
       2 | {}
(2 rows)

```
