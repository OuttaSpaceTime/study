---
wiki: sql/nullable-columns
section: Nullable foreign keys
kind: predict-output
env: pg
questions:
- Why does the INNER JOIN drop ann's row?
- The insert with parent_id NULL passed the FK check. What exactly does an FK constraint enforce for NULL values?
created: 2026-07-04
---

## Brief

ann is a top-level comment, bob and cid reply to her. Predict the rows each join returns.

## Setup

```sql
CREATE TABLE comments (id int PRIMARY KEY, author text, parent_id int REFERENCES comments(id));
INSERT INTO comments VALUES (1, 'ann', NULL), (2, 'bob', 1), (3, 'cid', 1);
```

## Stub

```sql
SELECT c.author, parent.author AS replies_to
FROM comments c
JOIN comments parent ON parent.id = c.parent_id
ORDER BY c.id;

SELECT c.author, parent.author AS replies_to
FROM comments c
LEFT JOIN comments parent ON parent.id = c.parent_id
ORDER BY c.id;
```

## Solution

```sql
SELECT c.author, parent.author AS replies_to
FROM comments c
JOIN comments parent ON parent.id = c.parent_id
ORDER BY c.id;

SELECT c.author, parent.author AS replies_to
FROM comments c
LEFT JOIN comments parent ON parent.id = c.parent_id
ORDER BY c.id;
```

## Expected Output

```
 author | replies_to 
--------+------------
 bob    | ann
 cid    | ann
(2 rows)

 author | replies_to 
--------+------------
 ann    | 
 bob    | ann
 cid    | ann
(3 rows)

```
