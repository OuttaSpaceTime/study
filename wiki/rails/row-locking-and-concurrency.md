---
title: Row locking and concurrency
aliases:
- with_lock
- Pessimistic locking in Rails
- Optimistic locking
- Database row locking
- MVCC
- Lost update
tags:
- rails
- postgres
- concurrency
- locking
- databases
created: '2026-06-25'
updated: '2026-06-25'
source_skill: study-walkthrough
flashcard_ids:
- cmqu0tx600008150m7a48y2lr
- cmqu0tyy80009150ma3fm8a5h
- cmqu0u0ef000a150muv3hmvrl
- cmqu0u1ur000b150m6ttrks13
- cmqu0u3eu000c150m44rrl72z
probe_sections:
- MVCC means readers and writers never block each other
- Implicit row locks make writers block writers
- Lost updates and why with_lock fixes them
- with_lock, lock!, and lock
- Why a transaction does not speed up parallel work
- Optimistic versus pessimistic locking
last_probed:
- with_lock, lock!, and lock
- Why a transaction does not speed up parallel work
- Optimistic versus pessimistic locking
- MVCC means readers and writers never block each other
- Implicit row locks make writers block writers
- Lost updates and why with_lock fixes them
review_interval: 4
next_review: '2026-07-07'
---

# Row locking and concurrency

## TL;DR

Postgres uses MVCC, so reads and writes never block each other. The only contention is **writer versus writer on the same row**. A bare `UPDATE` already takes an implicit row lock held until commit, so writers serialize automatically. That implicit lock is not enough for read-modify-write done in Ruby, which loses updates and needs `with_lock` (`SELECT ... FOR UPDATE`) to move the lock back to read time. A transaction is for correctness, not parallelism. See [[rails/database-transactions]] for the transaction side of this.

## MVCC means readers and writers never block each other

Postgres uses MVCC (Multi-Version Concurrency Control). The rule, [verbatim from the docs](https://www.postgresql.org/docs/current/mvcc-intro.html), is "reading never blocks writing and writing never blocks reading."

Concretely, the rule has two halves plus one exception:

- A **plain** `SELECT` never waits for a writer. It returns the last committed value (a snapshot), even while another transaction holds an uncommitted change to that row.
- A writer never waits for a plain reader. It ignores who is reading.
- The **only** pair that blocks is **writer versus writer** on the **same row**.

So a plain `Account.find(42)` issued while another transaction holds row 42 mid-update returns immediately with the old balance. Independent rows proceed fully in parallel.

## Implicit row locks make writers block writers

A bare `UPDATE` or `DELETE` takes an **implicit row-level lock** on the affected row the moment it runs, and holds it until the transaction ends. You do not need `with_lock` or `SELECT FOR UPDATE` for this to happen. A second transaction that tries to `UPDATE` the same row waits until the first commits or rolls back.

This was confirmed by probe. Two transactions both ran `UPDATE accounts SET balance = balance + 100 WHERE id = 42` with no explicit lock anywhere. The first held its transaction open for 3 seconds. The second, starting 1 second in, **blocked for ~2 seconds** until the first committed, then completed. Final balance was 200, both increments correctly applied.

> [Note] The implicit lock is taken at the moment the write statement executes, not when the transaction opens. That timing detail is exactly what makes read-modify-write unsafe (see below).

## Lost updates and why with_lock fixes them

The implicit lock is enough when the new value is computed **inside one SQL statement**:

```ruby
# good: read and write are one atomic statement in the DB
account.update!(balance: account.balance + 100)
# => UPDATE accounts SET balance = balance + 100 WHERE id = 42  (when written this way in SQL)
```

It is **not** enough when you read in Ruby, compute, then write back later:

```ruby
# bad: read-modify-write with a gap
acct = Account.find(42)            # SELECT balance -> reads 0
acct.balance = acct.balance + 100  # compute 100 in Ruby memory
acct.save!                         # UPDATE ... SET balance = 100
```

Two requests running this concurrently both `SELECT` balance 0 before either writes, because plain reads do not block and the implicit write lock is only taken at `save!`. Both compute 100, both write 100. The final balance is **100, not 200**, and one increment is silently lost. This is a **lost update**.

`with_lock` closes the gap by issuing a **locking read**:

```ruby
# good: SELECT ... FOR UPDATE locks the row at read time
acct.with_lock do
  acct.balance = acct.balance + 100
  acct.save!
end
```

`SELECT ... FOR UPDATE` is not a plain read. It announces "I intend to write this row", so Postgres treats it like a writer. The "readers never block" rule does not apply to it. When two requests both use `with_lock`, the second one's `FOR UPDATE` **blocks** until the first commits, and crucially, when it unblocks it **re-reads the fresh committed value** (100) rather than its stale snapshot (0). It then computes 200 and writes 200. `with_lock` fixes lost updates by doing both things at once. It serializes the writers and forces the late one to read current data.

## with_lock, lock!, and lock

Rails has three pessimistic-locking APIs. All three emit `SELECT ... FOR UPDATE`, and in all three the lock is held until the **surrounding transaction ends**. The lock duration is identical. They differ in **when and how the lock is acquired**, and in **who owns the transaction**.

```ruby
# (1) with_lock — lock! plus its own transaction wrapper
account.with_lock do
  account.update!(balance: account.balance + 100)
end

# (2) lock! — lock an already-loaded record; you must already be in a transaction
account.lock!
account.update!(balance: account.balance + 100)

# (3) lock (query) — acquire the lock at load time
account = Account.lock.find(42)
account.update!(balance: account.balance + 100)
```

- **`with_lock(&block)`** wraps the block in a transaction (opening one if needed), reloads the record `FOR UPDATE`, then yields. Self-contained, and the safe default because it **guarantees the transaction boundary exists**.
- **`lock!`** only reloads the already-loaded record `FOR UPDATE`. It does **not** open a transaction. Called outside a transaction it is useless: each statement auto-commits, so the lock is released the instant the reload returns and protects nothing. It is meaningful only **inside a transaction you opened yourself**. It reloads because your earlier plain `SELECT` may now be stale.
- **`lock` (query)** takes the lock at **load time**. `Account.lock.find(42)` issues one `SELECT ... FOR UPDATE` that *is* the load, so the row is locked from the first read with no gap. Also only useful inside a transaction.

Choosing between them:

- Know up front you will write the row: `Account.lock.find` (locked from the first read).
- Already holding an object and *then* decide to lock: `lock!` (reload-and-lock, inside your transaction).
- Want the lock bundled with its own transaction: `with_lock`.

## Why a transaction does not speed up parallel work

A transaction's purpose is atomicity and isolation, never speed or parallelism. Under contention it generally *hurts* throughput, because it holds every row lock it acquired until commit. The longer a transaction stays open, the longer those locks are held, and the more other writers on those rows are forced to wait.

The way to get parallelism is the opposite of one big transaction:

- Keep transactions **short**, so locks are released quickly.
- Touch **independent rows** where possible, so writers do not contend.
- Rely on MVCC, which already gives parallel reads for free.

Wrapping a large batch job in a single giant transaction does not make it parallel-safe-and-fast. It serializes writers on every contended row and balloons the lock-hold window.

> [Note] Deadlocks arise when two transactions take locks on multiple rows in inconsistent order (A then B versus B then A). Postgres detects them and aborts one transaction. The defense is acquiring locks in a consistent order. See [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html).

## Optimistic versus pessimistic locking

> [Note] The points in this section are practitioner consensus on *when* to choose each strategy, not a hard rule from the docs.

- **Pessimistic locking** (`with_lock` / `SELECT FOR UPDATE`) blocks competing writers up front. It wins for **write-heavy, high-conflict** rows, where retries would mostly be wasted. The cost is reduced concurrency on the locked row.
- **Optimistic locking** (Rails' `lock_version` column) lets writers proceed without locking and raises `StaleObjectError` if two writers collide, leaving you to retry. It wins for **read-heavy, low-conflict** data, where collisions are rare and retries are cheap.

Both are valid. Choose by the conflict rate on the data, not by habit.

## Related Concepts

- [[rails/database-transactions]]: atomicity, isolation levels, rollback semantics, and when to use a transaction.
- [[rails/upsert-and-concurrent-inserts]]: handling concurrent inserts and the race conditions unique constraints catch.

## References

- [PostgreSQL: Introduction to MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html): "reading never blocks writing and writing never blocks reading."
- [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html): row locks, `FOR UPDATE`, writer-blocks-writer, deadlock detection.
- [Rails API: ActiveRecord::Locking](https://api.rubyonrails.org/classes/ActiveRecord/Locking/Pessimistic.html): `with_lock` and `lock!` pessimistic locking.

**Practitioner / opinion:**

- [Implement optimistic locking in Rails](https://blog.kiprosh.com/implement-optimistic-locking-in-rails/): optimistic versus pessimistic tradeoffs.
