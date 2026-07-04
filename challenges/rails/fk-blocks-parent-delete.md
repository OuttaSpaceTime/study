---
wiki: rails/foreign-keys
section: Which row the constraint blocks from deletion
kind: predict-output
env: pg
questions:
- Which table holds the constraint, and why does that make the parent delete the blocked one?
- Why is deleting the child row always allowed?
created: 2026-07-03
---

## Brief

A foreign key on items.event_id references events, and one row exists on each side. The DO block tries to delete the event and silently swallows a foreign key violation if one fires. Predict both counts.

## Setup

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (id int PRIMARY KEY, event_id int REFERENCES events);
INSERT INTO events VALUES (1);
INSERT INTO items VALUES (10, 1);
```

## Stub

```sql
DO $$
BEGIN
  DELETE FROM events WHERE id = 1;
EXCEPTION WHEN foreign_key_violation THEN NULL;
END $$;

DELETE FROM items WHERE id = 10;

SELECT (SELECT count(*) FROM events) AS events_left,
       (SELECT count(*) FROM items) AS items_left;
```

## Solution

```sql
DO $$
BEGIN
  DELETE FROM events WHERE id = 1;
EXCEPTION WHEN foreign_key_violation THEN NULL;
END $$;

DELETE FROM items WHERE id = 10;

SELECT (SELECT count(*) FROM events) AS events_left,
       (SELECT count(*) FROM items) AS items_left;
```

## Expected Output

```
DO
DELETE 1
 events_left | items_left 
-------------+------------
           1 |          0
(1 row)

```
