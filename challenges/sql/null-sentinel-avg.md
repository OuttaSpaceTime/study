---
wiki: sql/nullable-columns
section: Sentinels masquerading as values
kind: predict-output
env: pg
questions:
- How does AVG treat NULL inputs, and what changed after the UPDATE?
- Why is the sentinel 0 worse than NULL for aggregate-heavy reads?
created: 2026-07-04
---

## Brief

One patient was never weighed. Predict both averages, before and after replacing the NULL with the sentinel 0.

## Setup

```sql
CREATE TABLE patients (name text, weight_kg numeric);
INSERT INTO patients VALUES ('ann', 70), ('bob', 90), ('cid', NULL);
```

## Stub

```sql
SELECT round(avg(weight_kg), 1) FROM patients;
UPDATE patients SET weight_kg = 0 WHERE weight_kg IS NULL;
SELECT round(avg(weight_kg), 1) FROM patients;
```

## Solution

```sql
SELECT round(avg(weight_kg), 1) FROM patients;
UPDATE patients SET weight_kg = 0 WHERE weight_kg IS NULL;
SELECT round(avg(weight_kg), 1) FROM patients;
```

## Expected Output

```
 round 
-------
  80.0
(1 row)

UPDATE 1
 round 
-------
  53.3
(1 row)

```
