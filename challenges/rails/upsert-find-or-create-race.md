---
wiki: rails/upsert-and-concurrent-inserts
section: find_or_create_by is not atomic
kind: predict-output
env: pg
questions:
- What single schema change turns this silent duplication into a catchable error?
- Once the failure is catchable, what are the two clean ways to handle it?
created: 2026-07-03
---

## Brief

Two jobs each run find_or_create_by against a table with no unique index. This replays their exact statement order in one session. Predict the final count.

## Setup

```sql
CREATE TABLE events (
  id serial PRIMARY KEY,
  user_id int,
  event_key text
);
```

## Stub

```sql
-- job A: find_or_create_by runs its SELECT
SELECT id FROM events WHERE user_id = 7 AND event_key = 'signup';
-- job B: find_or_create_by runs its SELECT
SELECT id FROM events WHERE user_id = 7 AND event_key = 'signup';
-- job A: found nothing, inserts
INSERT INTO events (user_id, event_key) VALUES (7, 'signup');
-- job B: found nothing, inserts
INSERT INTO events (user_id, event_key) VALUES (7, 'signup');
SELECT count(*) FROM events WHERE user_id = 7 AND event_key = 'signup';
```

## Solution

```sql
-- job A: find_or_create_by runs its SELECT
SELECT id FROM events WHERE user_id = 7 AND event_key = 'signup';
-- job B: find_or_create_by runs its SELECT
SELECT id FROM events WHERE user_id = 7 AND event_key = 'signup';
-- job A: found nothing, inserts
INSERT INTO events (user_id, event_key) VALUES (7, 'signup');
-- job B: found nothing, inserts
INSERT INTO events (user_id, event_key) VALUES (7, 'signup');
SELECT count(*) FROM events WHERE user_id = 7 AND event_key = 'signup';
```

## Expected Output

```
 id 
----
(0 rows)

 id 
----
(0 rows)

INSERT 0 1
INSERT 0 1
 count 
-------
     2
(1 row)

```
