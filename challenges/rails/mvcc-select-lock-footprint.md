---
wiki: rails/row-locking-and-concurrency
section: MVCC means readers and writers never block each other
kind: predict-output
env: pg
questions:
- Why can a plain SELECT never block or be blocked by an UPDATE on the same row?
- What does FOR UPDATE change about how Postgres treats the reader?
created: 2026-07-03
---

## Brief

Inside one transaction, a plain read of row 42 runs first, then a locking read of the same row. Predict which table-level lock modes pg_locks reports after each read.

## Setup

```sql
CREATE TABLE accounts (id int PRIMARY KEY, balance int);
INSERT INTO accounts VALUES (42, 0);
```

## Stub

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 42;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
SELECT balance FROM accounts WHERE id = 42 FOR UPDATE;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
COMMIT;
```

## Solution

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 42;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
SELECT balance FROM accounts WHERE id = 42 FOR UPDATE;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
COMMIT;
```

## Expected Output

```
BEGIN
 balance 
---------
       0
(1 row)

      mode       
-----------------
 AccessShareLock
(1 row)

 balance 
---------
       0
(1 row)

      mode       
-----------------
 AccessShareLock
 RowShareLock
(2 rows)

COMMIT
```
