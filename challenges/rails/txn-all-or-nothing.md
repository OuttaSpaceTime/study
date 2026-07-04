---
wiki: rails/database-transactions
section: What a transaction guarantees, and what it does not
kind: predict-output
env: pg
questions:
- Both UPDATEs printed UPDATE 1, so why does the final SELECT show the original balances?
- Why does opening this transaction not stop another session from updating the sender row at the same time?
created: 2026-07-03
---

## Brief

A money transfer runs inside an open transaction. Both UPDATEs report success and one SELECT runs before the ROLLBACK, one after. Predict what each SELECT prints.

## Setup

```sql
CREATE TABLE accounts (id int PRIMARY KEY, name text, balance int);
INSERT INTO accounts VALUES (1, 'sender', 100), (2, 'receiver', 0);
```

## Stub

```sql
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
SELECT name, balance FROM accounts ORDER BY id;
ROLLBACK;
SELECT name, balance FROM accounts ORDER BY id;
```

## Solution

```sql
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
SELECT name, balance FROM accounts ORDER BY id;
ROLLBACK;
SELECT name, balance FROM accounts ORDER BY id;
```

## Expected Output

```
BEGIN
UPDATE 1
UPDATE 1
   name   | balance 
----------+---------
 sender   |       0
 receiver |     100
(2 rows)

ROLLBACK
   name   | balance 
----------+---------
 sender   |     100
 receiver |       0
(2 rows)

```
