---
wiki: rails/upsert-and-concurrent-inserts
section: RETURNING returns only touched rows
kind: predict-output
env: pg
questions:
- Why does RETURNING report fewer rows than the VALUES list has?
- Why is id 2 absent even though only one input row was skipped?
created: 2026-07-03
---

## Brief

The table already contains the signup row with id 1. Predict how many rows RETURNING gives back for this three row batch and which ids they carry.

## Setup

```sql
CREATE TABLE events (id serial PRIMARY KEY, user_id int, event_key text,
                     UNIQUE (user_id, event_key));
INSERT INTO events (user_id, event_key) VALUES (7, 'signup');
```

## Stub

```sql
INSERT INTO events (user_id, event_key)
VALUES (7, 'signup'), (7, 'login'), (7, 'logout')
ON CONFLICT (user_id, event_key) DO NOTHING
RETURNING id;
```

## Solution

```sql
INSERT INTO events (user_id, event_key)
VALUES (7, 'signup'), (7, 'login'), (7, 'logout')
ON CONFLICT (user_id, event_key) DO NOTHING
RETURNING id;
```

## Expected Output

```
 id 
----
  3
  4
(2 rows)

INSERT 0 2
```
