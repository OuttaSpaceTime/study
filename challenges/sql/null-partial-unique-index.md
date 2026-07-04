---
wiki: sql/nullable-columns
section: Partial unique indexes
kind: write-code
env: pg
questions:
- Why can a plain UNIQUE (user_id, cancelled_at) not enforce one active subscription per user?
- Which rows does the partial index store, and among which rows is uniqueness checked?
created: 2026-07-04
---

## Brief

NULL cancelled_at means the subscription is active. Write the index that allows many cancelled rows per user but at most one active row.

## Setup

```sql
CREATE TABLE subscriptions (user_id int, cancelled_at timestamp);
```

## Stub

```sql
-- TODO: enforce at most one active (cancelled_at IS NULL) subscription per user

INSERT INTO subscriptions VALUES (7, NULL);
INSERT INTO subscriptions VALUES (7, '2025-09-01');
DO $$
BEGIN
  INSERT INTO subscriptions VALUES (7, NULL);
EXCEPTION WHEN unique_violation THEN NULL;
END $$;
SELECT user_id, cancelled_at FROM subscriptions ORDER BY cancelled_at;
```

## Solution

```sql
CREATE UNIQUE INDEX one_active_per_user
  ON subscriptions (user_id)
  WHERE cancelled_at IS NULL;

INSERT INTO subscriptions VALUES (7, NULL);
INSERT INTO subscriptions VALUES (7, '2025-09-01');
DO $$
BEGIN
  INSERT INTO subscriptions VALUES (7, NULL);
EXCEPTION WHEN unique_violation THEN NULL;
END $$;
SELECT user_id, cancelled_at FROM subscriptions ORDER BY cancelled_at;
```

## Expected Output

```
CREATE INDEX
INSERT 0 1
INSERT 0 1
DO
 user_id |    cancelled_at     
---------+---------------------
       7 | 2025-09-01 00:00:00
       7 | 
(2 rows)

```
