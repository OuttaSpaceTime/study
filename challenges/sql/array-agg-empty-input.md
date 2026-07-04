---
wiki: sql/array-agg
section: Empty input returns NULL, not {}
kind: predict-output
env: pg
questions:
- Why does the first query return a row while the second returns none?
- Which aggregate is the exception that returns a non-NULL value on empty input?
created: 2026-07-03
---

## Brief

Post 42 has no tags at all. Predict what each query returns, paying attention to both the row count and the aggregate value.

## Setup

```sql
CREATE TABLE post_tags (post_id int, tag text);
INSERT INTO post_tags VALUES (1, 'sql'), (1, 'postgres');
```

## Stub

```sql
SELECT array_agg(tag) FROM post_tags WHERE post_id = 42;

SELECT post_id, array_agg(tag) FROM post_tags WHERE post_id = 42 GROUP BY post_id;
```

## Solution

```sql
SELECT array_agg(tag) FROM post_tags WHERE post_id = 42;

SELECT post_id, array_agg(tag) FROM post_tags WHERE post_id = 42 GROUP BY post_id;
```

## Expected Output

```
 array_agg 
-----------
 
(1 row)

 post_id | array_agg 
---------+-----------
(0 rows)

```
