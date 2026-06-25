---
topic: transactions-and-locking
session: 2026-06-25-walkthrough
wiki: rails/row-locking-and-concurrency
created: 2026-06-25 15:00
---

## Prediction

A second transaction running a plain `UPDATE` on the same row (no `with_lock` / `SELECT FOR UPDATE` anywhere) will complete instantly, because a bare UPDATE takes no lock.

## Command

```bash
DB=txn_probe
dropdb --if-exists "$DB"; createdb "$DB"
psql -q "$DB" -c "CREATE TABLE accounts (id int primary key, balance int); INSERT INTO accounts VALUES (42, 0);"
# Session A: open txn, UPDATE row 42, hold 3s, commit
( psql -q "$DB" <<'SQL'
BEGIN;
UPDATE accounts SET balance = balance + 100 WHERE id = 42;
SELECT pg_sleep(3);
COMMIT;
SQL
) &
sleep 1   # let A grab the row first
# Session B: time how long its UPDATE on the SAME row waits
psql -q "$DB" -c "\timing on" <<'SQL'
BEGIN;
UPDATE accounts SET balance = balance + 100 WHERE id = 42;
COMMIT;
SQL
wait; psql -qtA "$DB" -c "SELECT balance FROM accounts WHERE id = 42;"; dropdb "$DB"
```

## Output

```
Time: 1999,078 ms (00:01,999)   # Session B's UPDATE — it BLOCKED ~2s
200                              # final balance, both +100 applied
```

## Takeaway

Prediction was wrong. A bare `UPDATE` takes an **implicit row-level lock** the instant it runs and holds it until the transaction ends. Session B's UPDATE blocked for ~2 seconds (the remainder of A's 3s hold), with zero explicit locking anywhere. Writers serialize on the same row automatically. The lock is taken at the write statement, not at `BEGIN` — which is exactly why read-modify-write in Ruby (read, compute, write later) still loses updates and needs `with_lock` to move the lock back to read time.
