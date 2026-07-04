---
wiki: sql/nullable-columns
section: UNIQUE does not constrain NULLs
kind: predict-output
env: pg
questions:
- Why does the UNIQUE constraint let both NULL inserts through?
- Which Postgres 15 clause opts into treating NULLs as equal in a unique constraint?
created: 2026-07-04
---

## Brief

An email column with a UNIQUE constraint receives two NULL inserts. Predict whether the second insert fails and what the final count is.

## Stub

```sql
CREATE TABLE users (email text UNIQUE);
INSERT INTO users VALUES (NULL);
INSERT INTO users VALUES (NULL);
SELECT count(*) FROM users WHERE email IS NULL;
```

## Solution

```sql
CREATE TABLE users (email text UNIQUE);
INSERT INTO users VALUES (NULL);
INSERT INTO users VALUES (NULL);
SELECT count(*) FROM users WHERE email IS NULL;
```

## Expected Output

```
CREATE TABLE
INSERT 0 1
INSERT 0 1
 count 
-------
     2
(1 row)

```
