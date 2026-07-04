---
wiki: rails/upsert-and-concurrent-inserts
section: ON CONFLICT DO NOTHING vs DO UPDATE
kind: write-code
env: pg
questions:
- Which row does the excluded pseudo table hold, and which row does the plain table name reference?
- What happens when the collision lands on a unique constraint other than the named arbiter?
created: 2026-07-03
---

## Brief

The table already holds a count of 5 for this key and an incoming batch carries 3 more. Complete the DO UPDATE so the upsert adds the incoming count onto the existing one.

## Setup

```sql
CREATE TABLE event_counts (user_id int, event_key text, count int,
                           UNIQUE (user_id, event_key));
INSERT INTO event_counts VALUES (7, 'signup', 5);
```

## Stub

```sql
INSERT INTO event_counts (user_id, event_key, count)
VALUES (7, 'signup', 3)
ON CONFLICT (user_id, event_key)
DO UPDATE SET count = 0; -- TODO: existing count plus incoming count
SELECT count FROM event_counts;
```

## Solution

```sql
INSERT INTO event_counts (user_id, event_key, count)
VALUES (7, 'signup', 3)
ON CONFLICT (user_id, event_key)
DO UPDATE SET count = event_counts.count + excluded.count;
SELECT count FROM event_counts;
```

## Expected Output

```
INSERT 0 1
 count 
-------
     8
(1 row)

```
