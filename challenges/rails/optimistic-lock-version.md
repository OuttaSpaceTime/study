---
wiki: rails/row-locking-and-concurrency
section: Optimistic versus pessimistic locking
kind: predict-output
env: pg
questions:
- How does Rails detect the stale write here, and what exception does it raise?
- For which conflict profile does optimistic locking beat with_lock?
created: 2026-07-03
---

## Brief

Two requests both loaded the row while lock_version was 0, then both save. This is the SQL Rails emits for lock_version. Predict both command tags and the final row.

## Setup

```sql
CREATE TABLE accounts (id int PRIMARY KEY, balance int, lock_version int NOT NULL DEFAULT 0);
INSERT INTO accounts VALUES (42, 0, 0);
```

## Stub

```sql
UPDATE accounts SET balance = 100, lock_version = 1
WHERE id = 42 AND lock_version = 0;
UPDATE accounts SET balance = 250, lock_version = 1
WHERE id = 42 AND lock_version = 0;
SELECT balance, lock_version FROM accounts WHERE id = 42;
```

## Solution

```sql
UPDATE accounts SET balance = 100, lock_version = 1
WHERE id = 42 AND lock_version = 0;
UPDATE accounts SET balance = 250, lock_version = 1
WHERE id = 42 AND lock_version = 0;
SELECT balance, lock_version FROM accounts WHERE id = 42;
```

## Expected Output

```
UPDATE 1
UPDATE 0
 balance | lock_version 
---------+--------------
     100 |            1
(1 row)

```
