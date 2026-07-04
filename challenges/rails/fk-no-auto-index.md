---
wiki: rails/foreign-keys
section: A foreign key does not create an index
kind: predict-output
env: pg
questions:
- Whose deletes get slow when items.event_id has no index, and why?
- Which Rails migration helper adds the index for you, and which one leaves it to you?
created: 2026-07-03
---

## Brief

The setup creates events and items with a foreign key on items.event_id. Predict every index that exists on the two tables.

## Setup

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (id int PRIMARY KEY, event_id int NOT NULL REFERENCES events);
```

## Stub

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('events', 'items')
ORDER BY tablename, indexname;
```

## Solution

```sql
SELECT tablename, indexname
FROM pg_indexes
WHERE tablename IN ('events', 'items')
ORDER BY tablename, indexname;
```

## Expected Output

```
 tablename |  indexname  
-----------+-------------
 events    | events_pkey
 items     | items_pkey
(2 rows)

```
