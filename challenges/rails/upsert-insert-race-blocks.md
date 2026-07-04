---
wiki: rails/upsert-and-concurrent-inserts
section: The race between two concurrent inserts
kind: predict-output
env: pg
questions:
- Why does job B block instead of failing immediately with a unique violation?
- What decides whether B eventually raises 23505 or inserts successfully?
created: 2026-07-03
---

## Brief

Job A inserts a row inside an open dblink transaction and never commits. The local session plays job B with a 300ms lock timeout, then A rolls back and B tries again. Predict what lands in outcomes and whether the final insert succeeds.

## Setup

```sql
CREATE EXTENSION dblink;
CREATE TABLE events (user_id int, event_key text);
CREATE UNIQUE INDEX ON events (user_id, event_key);
CREATE TABLE outcomes (note text);
```

## Stub

```sql
SELECT dblink_connect('job_a', 'dbname=' || current_database());
SELECT dblink_exec('job_a', 'BEGIN; INSERT INTO events VALUES (7, ''signup'')');
SET lock_timeout = '300ms';
DO $$
BEGIN
  INSERT INTO events VALUES (7, 'signup');
EXCEPTION
  WHEN lock_not_available THEN INSERT INTO outcomes VALUES ('B blocked while A was uncommitted');
  WHEN unique_violation   THEN INSERT INTO outcomes VALUES ('B failed with 23505 immediately');
END $$;
SELECT dblink_exec('job_a', 'ROLLBACK');
INSERT INTO events VALUES (7, 'signup');
SELECT note FROM outcomes;
```

## Solution

```sql
SELECT dblink_connect('job_a', 'dbname=' || current_database());
SELECT dblink_exec('job_a', 'BEGIN; INSERT INTO events VALUES (7, ''signup'')');
SET lock_timeout = '300ms';
DO $$
BEGIN
  INSERT INTO events VALUES (7, 'signup');
EXCEPTION
  WHEN lock_not_available THEN INSERT INTO outcomes VALUES ('B blocked while A was uncommitted');
  WHEN unique_violation   THEN INSERT INTO outcomes VALUES ('B failed with 23505 immediately');
END $$;
SELECT dblink_exec('job_a', 'ROLLBACK');
INSERT INTO events VALUES (7, 'signup');
SELECT note FROM outcomes;
```

## Expected Output

```
 dblink_connect 
----------------
 OK
(1 row)

 dblink_exec 
-------------
 INSERT 0 1
(1 row)

SET
DO
 dblink_exec 
-------------
 ROLLBACK
(1 row)

INSERT 0 1
               note                
-----------------------------------
 B blocked while A was uncommitted
(1 row)

```
