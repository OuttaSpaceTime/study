---
wiki: rails/row-locking-and-concurrency
section: Implicit row locks make writers block writers
kind: predict-output
env: pg
questions:
- When is the implicit row lock taken, and when is it released?
- Why does Ruby read-modify-write still lose updates despite this lock, and what moves the lock to read time?
created: 2026-07-03
---

## Brief

A bare UPDATE with no explicit locking anywhere. Predict what the lock query reports while the transaction is still open.

## Setup

```sql
CREATE TABLE accounts (id int PRIMARY KEY, balance int);
INSERT INTO accounts VALUES (42, 0);
```

## Stub

```sql
BEGIN;
UPDATE accounts SET balance = balance + 100 WHERE id = 42;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
COMMIT;
```

## Solution

```sql
BEGIN;
UPDATE accounts SET balance = balance + 100 WHERE id = 42;
SELECT mode FROM pg_locks
WHERE relation = 'accounts'::regclass AND granted
ORDER BY mode;
COMMIT;
```

## Expected Output

```
BEGIN
UPDATE 1
       mode       
------------------
 RowExclusiveLock
(1 row)

COMMIT
```
