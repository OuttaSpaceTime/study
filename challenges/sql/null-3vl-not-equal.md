---
wiki: sql/nullable-columns
section: Three-valued logic is the root cause
kind: predict-output
env: pg
questions:
- What does a comparison involving NULL evaluate to, and how does WHERE treat that result?
- Why does IS DISTINCT FROM return the NULL row when != does not?
created: 2026-07-04
---

## Brief

Three users, one with an unknown status. Predict which names each query returns.

## Setup

```sql
CREATE TABLE users (name text, status text);
INSERT INTO users VALUES ('ann', 'active'), ('bob', 'inactive'), ('cid', NULL);
```

## Stub

```sql
SELECT name FROM users WHERE status != 'active';
SELECT name FROM users WHERE status IS DISTINCT FROM 'active';
```

## Solution

```sql
SELECT name FROM users WHERE status != 'active';
SELECT name FROM users WHERE status IS DISTINCT FROM 'active';
```

## Expected Output

```
 name 
------
 bob
(1 row)

 name 
------
 bob
 cid
(2 rows)

```
