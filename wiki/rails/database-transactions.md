---
title: Database transactions
aliases:
- Rails transactions
- ActiveRecord transactions
- ActiveRecord::Rollback
- Transaction isolation levels
tags:
- rails
- postgres
- transactions
- databases
created: '2026-06-25'
updated: '2026-06-25'
source_skill: study-walkthrough
flashcard_ids:
- cmqu0tqlr0004150miu3h07bc
- cmqu0ts1l0005150mcb26qlt0
- cmqu0ttxx0006150myqedtn6q
- cmqu0tvnw0007150msfy24wz5
probe_sections:
- What a transaction guarantees, and what it does not
- Isolation levels and the anomalies each allows
- Never put slow or external calls inside a transaction
- Idempotency and effects outside the transaction
- Rails rollback-on-exception
- Nested transactions and savepoints
last_probed:
- What a transaction guarantees, and what it does not
- Idempotency and effects outside the transaction
- Rails rollback-on-exception
- Nested transactions and savepoints
- Isolation levels and the anomalies each allows
- Never put slow or external calls inside a transaction
review_interval: 8
next_review: '2026-07-11'
---

# Database transactions

## TL;DR

A transaction is a **correctness** tool, not a performance or parallelism tool. It guarantees that a group of writes either all commit or all roll back (atomicity), and that each transaction sees a consistent view of the data (isolation). It is **not** a mutex and does not serialize concurrent work by itself. Reach for it when several dependent writes must succeed or fail together. Do not reach for it to "protect against parallelism" (that is the job of locking, see [[rails/row-locking-and-concurrency]]), and never put slow or external work inside one.

## What a transaction guarantees, and what it does not

```ruby
ActiveRecord::Base.transaction do
  sender.update!(balance: sender.balance - 100)
  receiver.update!(balance: receiver.balance + 100)
end
```

If the second `update!` raises, the first is rolled back too. Both writes land or neither does. Without the wrapper, the sender would be debited while the receiver is never credited, and money would vanish.

What a transaction guarantees (ACID):

- **Atomicity.** All statements commit or none do.
- **Consistency.** Constraints hold at commit.
- **Isolation.** Each transaction sees a consistent snapshot, not other transactions' uncommitted work.
- **Durability.** Once committed, it survives a crash.

What it does **not** guarantee is a lock. Opening a transaction does not keep other workers out of the database, and it does not by itself serialize concurrent work on the same data. If you need to coordinate concurrent access to a row, that is the job of explicit locking, not merely of being inside a transaction. See [[rails/row-locking-and-concurrency]].

## Isolation levels and the anomalies each allows

Postgres has [four named isolation levels but only two distinct behaviors](https://www.postgresql.org/docs/current/transaction-iso.html) (Read Uncommitted behaves as Read Committed).

- **Read Committed** (the default). Each statement sees a snapshot taken when **that statement** begins. Two successive `SELECT`s in the same transaction can return different data. Still allows nonrepeatable reads, phantom reads, and serialization anomalies (the standard's lost update and write skew live under this umbrella).
- **Repeatable Read.** One snapshot taken at the transaction's first statement. Prevents dirty, nonrepeatable, and phantom reads, but still allows serialization anomalies (write skew).
- **Serializable.** Behaves as if transactions ran one at a time, enforced by Serializable Snapshot Isolation. Applications must be prepared to **retry** on serialization failures.

So if you run the same `SELECT count(*)` twice inside one Read Committed transaction and get different numbers, that is expected, not a bug. The default snapshot is per-statement.

## Never put slow or external calls inside a transaction

```ruby
# bad
ActiveRecord::Base.transaction do
  order.update!(status: "paying")   # takes a row lock on the order
  PaymentGateway.charge!(order)     # external HTTP call, ~2s, maybe much longer if the service is slow or down
  order.update!(status: "paid")
end
```

During that HTTP call, two things are held hostage until it returns:

1. The **row lock** on the order, blocking any other writer of that row.
2. The **database connection**, checked out of Rails' fixed-size connection pool for the whole duration.

Under load this is how a slow third party becomes a site-wide outage. Every web thread running this parks on the gateway, each holding a connection, the pool drains, and new requests cannot get a connection at all.

Move external and slow work **outside** the transaction. Do it before opening the transaction, or in an `after_commit` callback.

## Idempotency and effects outside the transaction

Moving the charge outside the transaction creates a new problem, and idempotency is the answer to it.

A transaction's atomicity is the safety net for effects **inside the database**. It can roll back rows. It is powerless over effects **outside** the database. It cannot un-charge a card, un-send an email, or un-call another service, because those already happened the moment the call returned. So anything reaching beyond the DB needs a different kind of retry safety.

The failure mode looks like this. The `charge!` succeeds, then the network drops before your code records `status: "paid"`, so the job retries from the top and calls `charge!` **again**, double-charging the customer.

**Idempotency** means designing the operation so calling it twice has the same effect as calling it once. In practice that is an **idempotency key**, a stable identifier sent with the request (for example `"charge-order-#{order.id}"`). The gateway remembers keys it has seen and, on a retry with the same key, returns the *original* result instead of charging again. The dedup can also live on your side as a unique column on a `charges` table. Either way the principle is the same. Same key, same effect, no double-charge.

The relationship in one line. **Atomicity protects the DB side, and idempotency protects the non-DB side.** You need both precisely because external calls do not belong inside the transaction.

## Rails rollback-on-exception

- A `transaction` block rolls back when **any exception is raised** inside it, and re-raises that exception to the caller.
- `raise ActiveRecord::Rollback` is the one exception that triggers a rollback but is **swallowed** by the block, so it does not propagate to your caller. Use it to abort a transaction without surfacing an error.
- Rails uses a **connection pool**, one connection per thread. Keep your thread count at or below the pool size or you exhaust the pool.

## Nested transactions and savepoints

There is no such thing as a truly independent nested transaction in most databases. There is only ever **one** real transaction, and ActiveRecord emulates nesting with **savepoints**.

A savepoint is a named marker inside an already-open transaction that you can roll back to **without aborting the whole transaction**. In raw SQL:

```sql
BEGIN;
UPDATE users SET name = 'A' WHERE id = 1;
SAVEPOINT sp1;                       -- marker
UPDATE users SET name = 'B' WHERE id = 1;
ROLLBACK TO SAVEPOINT sp1;           -- undo back to the marker only
COMMIT;                              -- 'A' survives and commits
```

Only the work done *after* the savepoint is undone. Everything before it stays, and the transaction is still open and commits normally.

**The footgun.** A bare nested `transaction` block does **not** create a savepoint. It silently joins the parent, so it has no rollback boundary of its own:

```ruby
# bad: the inner rollback is a silent no-op
ActiveRecord::Base.transaction do
  user.update!(name: "A")
  ActiveRecord::Base.transaction do      # no requires_new -> joins parent, no SAVEPOINT
    user.update!(name: "B")
    raise ActiveRecord::Rollback         # swallowed; outer never hears it; nothing to roll back to
  end
end
# final name: "B"  -- both writes commit
```

Two facts combine to produce this. The inner block has no boundary of its own (it joined the parent), and `ActiveRecord::Rollback` is swallowed by the inner block, so the outer block never sees an exception and there is no savepoint to roll back to. Both writes commit.

Pass `requires_new: true` to make the inner block emit a real `SAVEPOINT`, giving it a rollback boundary:

```ruby
# good: the inner block rolls back independently
ActiveRecord::Base.transaction do
  user.update!(name: "A")
  ActiveRecord::Base.transaction(requires_new: true) do   # issues SAVEPOINT
    user.update!(name: "B")
    raise ActiveRecord::Rollback                            # ROLLBACK TO SAVEPOINT
  end
end
# final name: "A"  -- inner undone, outer committed
```

> [Note] Even with `requires_new: true` it is a savepoint, not a truly independent transaction. A real (non-`ActiveRecord::Rollback`) exception raised in the inner block still propagates and aborts the outer transaction unless you rescue it.

## Related Concepts

- [[rails/row-locking-and-concurrency]]: MVCC, row locks, lost updates, and why a transaction does not speed up parallel work.
- [[rails/upsert-and-concurrent-inserts]]: handling concurrent inserts and the race conditions unique constraints catch.
- [[rails/foreign-keys]]: DB-level integrity that, like transactions, lives below the application layer.

## References

- [PostgreSQL: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html): the four levels, Read Committed default, and the anomaly table.
- [Rails API: ActiveRecord::Transactions](https://api.rubyonrails.org/classes/ActiveRecord/Transactions/ClassMethods.html): rollback-on-exception, `ActiveRecord::Rollback`, `requires_new` savepoints.

**Practitioner / opinion:**

- [Postgres transaction pitfalls for Rails developers](https://aboobacker.in/2022/04/12/postgres-transaction-pitfalls-for-rails-developers.html): network calls in callbacks, long transactions, idempotency.
