---
wiki: rails/row-locking-and-concurrency
section: Lost updates and why with_lock fixes them
kind: predict-output
env: pg
questions:
- At which statement would with_lock make request B block, and what does B read when it unblocks?
- Why does the implicit lock taken by each UPDATE not prevent this?
created: 2026-07-03
---

## Brief

Two concurrent requests each ran Account.find(42), computed balance + 100 in Ruby, and saved. This replays their exact statement order in one session. Predict the final balance.

## Setup

```sql
CREATE TABLE accounts (id int PRIMARY KEY, balance int);
INSERT INTO accounts VALUES (42, 0);
```

## Stub

```sql
-- request A: acct = Account.find(42)
SELECT balance FROM accounts WHERE id = 42;
-- request B: acct = Account.find(42)
SELECT balance FROM accounts WHERE id = 42;
-- request A: acct.save! after computing 0 + 100 in Ruby
UPDATE accounts SET balance = 100 WHERE id = 42;
-- request B: acct.save! after computing 0 + 100 in Ruby
UPDATE accounts SET balance = 100 WHERE id = 42;
SELECT balance FROM accounts WHERE id = 42;
```

## Solution

```sql
-- request A: acct = Account.find(42)
SELECT balance FROM accounts WHERE id = 42;
-- request B: acct = Account.find(42)
SELECT balance FROM accounts WHERE id = 42;
-- request A: acct.save! after computing 0 + 100 in Ruby
UPDATE accounts SET balance = 100 WHERE id = 42;
-- request B: acct.save! after computing 0 + 100 in Ruby
UPDATE accounts SET balance = 100 WHERE id = 42;
SELECT balance FROM accounts WHERE id = 42;
```

## Expected Output

```
 balance 
---------
       0
(1 row)

 balance 
---------
       0
(1 row)

UPDATE 1
UPDATE 1
 balance 
---------
     100
(1 row)

```
