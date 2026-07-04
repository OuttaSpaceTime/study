---
wiki: sql/array-agg
section: array_agg vs jsonb_agg
kind: predict-output
env: pg
questions:
- What constraint does array_agg place on its elements that jsonb_agg does not?
- When would you reach for jsonb_agg over array_agg?
created: 2026-07-04
---

## Brief

The same two rows are collected once as a Postgres array and once as JSON records. Predict the shape of each result.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, product text, created_at date);
INSERT INTO orders (product, created_at) VALUES ('apple', '2026-01-05'), ('pear', '2026-01-07');
```

## Stub

```sql
SELECT array_agg(product ORDER BY product) FROM orders;

SELECT jsonb_agg(jsonb_build_object('product', product, 'at', created_at) ORDER BY product) FROM orders;
```

## Solution

```sql
SELECT array_agg(product ORDER BY product) FROM orders;

SELECT jsonb_agg(jsonb_build_object('product', product, 'at', created_at) ORDER BY product) FROM orders;
```

## Expected Output

```
  array_agg   
--------------
 {apple,pear}
(1 row)

                                      jsonb_agg                                      
-------------------------------------------------------------------------------------
 [{"at": "2026-01-05", "product": "apple"}, {"at": "2026-01-07", "product": "pear"}]
(1 row)

```
