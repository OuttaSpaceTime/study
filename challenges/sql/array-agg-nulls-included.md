---
wiki: sql/array-agg
section: NULLs are included by default
kind: predict-output
env: pg
questions:
- How does array_agg treat NULL inputs compared to SUM or AVG?
- Which clause drops the NULLs from the array without filtering the whole query?
created: 2026-07-03
---

## Brief

One of the three orders has a NULL product. Predict what the aggregated array contains.

## Setup

```sql
CREATE TABLE orders (id serial PRIMARY KEY, product text);
INSERT INTO orders (product) VALUES ('apple'), (NULL), ('pear');
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
-------------------
 {apple,NULL,pear}
(1 row)

```
