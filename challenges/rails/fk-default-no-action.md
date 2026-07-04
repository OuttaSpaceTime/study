---
wiki: rails/foreign-keys
section: The four referential actions and the real default
kind: predict-output
env: pg
questions:
- Which referential action does Postgres store when the FK has no ON DELETE clause, and how do you get it from Rails?
- Why does the myth that RESTRICT is the default survive in everyday use?
created: 2026-07-03
---

## Brief

The setup declares the foreign key with no ON DELETE clause, exactly what a bare add_foreign_key emits. Predict which referential action Postgres stored for it.

## Setup

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (id int PRIMARY KEY, event_id int REFERENCES events);
```

## Stub

```sql
SELECT conname,
       CASE confdeltype
         WHEN 'a' THEN 'NO ACTION'
         WHEN 'r' THEN 'RESTRICT'
         WHEN 'c' THEN 'CASCADE'
         WHEN 'n' THEN 'SET NULL'
       END AS on_delete
FROM pg_constraint
WHERE contype = 'f';
```

## Solution

```sql
SELECT conname,
       CASE confdeltype
         WHEN 'a' THEN 'NO ACTION'
         WHEN 'r' THEN 'RESTRICT'
         WHEN 'c' THEN 'CASCADE'
         WHEN 'n' THEN 'SET NULL'
       END AS on_delete
FROM pg_constraint
WHERE contype = 'f';
```

## Expected Output

```
       conname       | on_delete 
---------------------+-----------
 items_event_id_fkey | NO ACTION
(1 row)

```
