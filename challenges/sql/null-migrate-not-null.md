---
wiki: sql/nullable-columns
section: Migrating to NOT NULL is expensive
kind: write-code
env: pg
questions:
- Why must the CHECK constraint be added with NOT VALID while row 2 still holds a NULL?
- What does Postgres 12+ do with the validated CHECK when you run SET NOT NULL?
created: 2026-07-03
---

## Brief

The status column still contains a NULL and the table is too big for a locking scan. Complete step 1 of the online NOT NULL migration so it succeeds while row 2 is still NULL.

## Setup

```sql
CREATE TABLE users (id int, status text);
INSERT INTO users VALUES (1, 'active'), (2, NULL);
```

## Stub

```sql
-- TODO: add a constraint users_status_not_null checking status IS NOT NULL,
-- skipping validation of existing rows

UPDATE users SET status = 'unknown' WHERE status IS NULL;
ALTER TABLE users VALIDATE CONSTRAINT users_status_not_null;
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

## Solution

```sql
ALTER TABLE users ADD CONSTRAINT users_status_not_null
  CHECK (status IS NOT NULL) NOT VALID;

UPDATE users SET status = 'unknown' WHERE status IS NULL;
ALTER TABLE users VALIDATE CONSTRAINT users_status_not_null;
ALTER TABLE users ALTER COLUMN status SET NOT NULL;
```

## Expected Output

```
ALTER TABLE
UPDATE 1
ALTER TABLE
ALTER TABLE
```
