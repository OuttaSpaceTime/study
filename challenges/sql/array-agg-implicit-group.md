---
wiki: sql/array-agg
section: No GROUP BY means one implicit group
kind: predict-output
env: pg
questions:
- How many rows does an aggregate query without GROUP BY return, and why?
- What would change if you added GROUP BY product to this query?
created: 2026-07-03
---

## Brief

Three rows, an aggregate, and no GROUP BY. Predict how many rows come back and what the single value contains.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, product text);
INSERT INTO orders (product) VALUES ('apple'), ('pear'), ('apple');
```

## Stub

```sql
SELECT array_agg(product) FROM orders;
```

## Solution

```sql
SELECT array_agg(product) FROM orders;
```

## Expected Output

```
     array_agg      
--------------------
 {apple,pear,apple}
(1 row)

```
