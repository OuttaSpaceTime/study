---
wiki: rails/database-transactions
section: Isolation levels and the anomalies each allows
kind: predict-output
env: pg
questions:
- Which anomaly does the second SELECT demonstrate, and which isolation level would make both SELECTs return 100?
- Which anomaly can still occur under Repeatable Read, and what must an application running Serializable be prepared to do?
created: 2026-07-03
---

## Brief

A transaction reads a balance twice at the default isolation level. Between the two reads, dblink_exec opens a second connection that updates and commits the row. Predict both SELECT results.

## Setup

```sql
CREATE EXTENSION dblink;
CREATE TABLE accounts (id int PRIMARY KEY, balance int);
INSERT INTO accounts VALUES (1, 100);
```

## Stub

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 1;
SELECT dblink_exec('dbname=' || current_database(), 'UPDATE accounts SET balance = 200 WHERE id = 1');
SELECT balance FROM accounts WHERE id = 1;
COMMIT;
```

## Solution

```sql
BEGIN;
SELECT balance FROM accounts WHERE id = 1;
SELECT dblink_exec('dbname=' || current_database(), 'UPDATE accounts SET balance = 200 WHERE id = 1');
SELECT balance FROM accounts WHERE id = 1;
COMMIT;
```

## Expected Output

```
BEGIN
 balance 
---------
     100
(1 row)

 dblink_exec 
-------------
 UPDATE 1
(1 row)

 balance 
---------
     200
(1 row)

COMMIT
```
