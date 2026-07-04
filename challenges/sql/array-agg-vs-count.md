---
wiki: sql/array-agg
section: What array_agg collects and the implicit single-group rule
kind: predict-output
env: pg
questions:
- What does array_agg preserve per group that COUNT throws away?
- How does this let one query return both the group and its members without a second round-trip?
created: 2026-07-04
---

## Brief

COUNT and array_agg run side by side over the same groups. Predict what each column contains per user.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, user_id int, product text);
INSERT INTO orders (user_id, product) VALUES (1, 'apple'), (1, 'pear'), (2, 'apple');
```

## Stub

```sql
SELECT user_id, count(*), array_agg(product ORDER BY product) AS products
FROM orders
GROUP BY user_id
ORDER BY user_id;
```

## Solution

```sql
SELECT user_id, count(*), array_agg(product ORDER BY product) AS products
FROM orders
GROUP BY user_id
ORDER BY user_id;
```

## Expected Output

```
 user_id | count |   products   
---------+-------+--------------
       1 |     2 | {apple,pear}
       2 |     1 | {apple}
(2 rows)

```
