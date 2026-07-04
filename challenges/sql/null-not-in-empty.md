---
wiki: sql/nullable-columns
section: The NOT IN trap
kind: predict-output
env: pg
questions:
- Expand id NOT IN (2, NULL) into its AND conjuncts. Why can the predicate never be TRUE?
- Why is NOT EXISTS immune to the NULL in the subquery?
created: 2026-07-04
---

## Brief

The cancelled orders list contains one NULL user_id. Predict what each query returns for the three users.

## Setup

```sql
CREATE TABLE users (id int, name text);
INSERT INTO users VALUES (1, 'ann'), (2, 'bob'), (3, 'cid');
CREATE TABLE cancelled_orders (user_id int);
INSERT INTO cancelled_orders VALUES (2), (NULL);
```

## Stub

```sql
SELECT name FROM users
WHERE id NOT IN (SELECT user_id FROM cancelled_orders);

SELECT name FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM cancelled_orders c WHERE c.user_id = u.id
);
```

## Solution

```sql
SELECT name FROM users
WHERE id NOT IN (SELECT user_id FROM cancelled_orders);

SELECT name FROM users u
WHERE NOT EXISTS (
  SELECT 1 FROM cancelled_orders c WHERE c.user_id = u.id
);
```

## Expected Output

```
 name 
------
(0 rows)

 name 
------
 ann
 cid
(2 rows)

```
