---
wiki: rails/foreign-keys
section: RESTRICT vs NO ACTION is only about deferrability
kind: write-code
env: pg
questions:
- When does the deferred foreign key check actually run in this script?
- Why would ON DELETE RESTRICT combined with DEFERRABLE not help here?
created: 2026-07-03
---

## Brief

The transaction deletes the parent before the child, so an orphan exists mid-transaction. Change the constraint declaration so the whole script commits cleanly.

## Stub

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (
  id int PRIMARY KEY,
  event_id int REFERENCES events  -- TODO: let the parent-first delete below survive
);
INSERT INTO events VALUES (42);
INSERT INTO items VALUES (1, 42);

BEGIN;
DELETE FROM events WHERE id = 42;
DELETE FROM items WHERE event_id = 42;
COMMIT;
```

## Solution

```sql
CREATE TABLE events (id int PRIMARY KEY);
CREATE TABLE items (
  id int PRIMARY KEY,
  event_id int REFERENCES events DEFERRABLE INITIALLY DEFERRED
);
INSERT INTO events VALUES (42);
INSERT INTO items VALUES (1, 42);

BEGIN;
DELETE FROM events WHERE id = 42;
DELETE FROM items WHERE event_id = 42;
COMMIT;
```

## Expected Output

```
CREATE TABLE
CREATE TABLE
INSERT 0 1
INSERT 0 1
BEGIN
DELETE 1
DELETE 1
COMMIT
```
