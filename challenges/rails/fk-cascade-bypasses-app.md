---
wiki: rails/foreign-keys
section: on_delete vs dependent and which side effects decide
kind: predict-output
env: pg
questions:
- Why does the command tag report DELETE 1 when three item rows also vanished?
- Why can an after_destroy callback on the child never run when the DB cascade removes it?
created: 2026-07-03
---

## Brief

The foreign key declares ON DELETE CASCADE and the event has three items. Predict the command tag of the DELETE and the remaining item count.

## Setup

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (id int PRIMARY KEY, event_id int REFERENCES events ON DELETE CASCADE);
INSERT INTO events VALUES (1);
INSERT INTO items VALUES (10, 1), (11, 1), (12, 1);
```

## Stub

```sql
DELETE FROM events WHERE id = 1;
SELECT count(*) FROM items;
```

## Solution

```sql
DELETE FROM events WHERE id = 1;
SELECT count(*) FROM items;
```

## Expected Output

```
DELETE 1
 count 
-------
     0
(1 row)

```
