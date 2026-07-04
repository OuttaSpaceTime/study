---
wiki: rails/database-transactions
section: Idempotency and effects outside the transaction
kind: write-code
env: pg
questions:
- Why does atomicity alone not prevent the double charge when the job retries?
- Where does the dedup live when the payment gateway supports idempotency keys itself?
created: 2026-07-03
---

## Brief

A charge is recorded with an idempotency key, then the job retries the exact same insert after a network drop. Make the retry a no-op so the customer is charged once.

## Setup

```sql
CREATE TABLE charges (id serial PRIMARY KEY, idempotency_key text UNIQUE NOT NULL, amount int NOT NULL);
```

## Stub

```sql
INSERT INTO charges (idempotency_key, amount) VALUES ('charge-order-7', 100);

INSERT INTO charges (idempotency_key, amount) VALUES ('charge-order-7', 100); -- TODO: make this retry a no-op instead of an error

SELECT count(*) AS charges, sum(amount) AS charged FROM charges;
```

## Solution

```sql
INSERT INTO charges (idempotency_key, amount) VALUES ('charge-order-7', 100);

INSERT INTO charges (idempotency_key, amount) VALUES ('charge-order-7', 100)
ON CONFLICT (idempotency_key) DO NOTHING;

SELECT count(*) AS charges, sum(amount) AS charged FROM charges;
```

## Expected Output

```
INSERT 0 1
INSERT 0 0
 charges | charged 
---------+---------
       1 |     100
(1 row)

```
