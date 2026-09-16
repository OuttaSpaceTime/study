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
updated: '2026-07-29'
source_skill: study-walkthrough
flashcard_ids:
- cmqu0tx600008150m7a48y2lr
- cmqu0tyy80009150ma3fm8a5h
- cmqu0u0ef000a150muv3hmvrl
- cmqu0u1ur000b150m6ttrks13
- cmqu0u3eu000c150m44rrl72z
---

# Row locking and concurrency

## TL;DR

Postgres uses MVCC, so reads and writes never block each other. The only contention is **writer versus writer on the same row**. A bare `UPDATE` already takes an implicit row lock held until commit, so writers serialize automatically. That implicit lock is not enough for read-modify-write done in Ruby, which loses updates and needs `with_lock` (`SELECT ... FOR UPDATE`) to move the lock back to read time. A transaction is for correctness, not parallelism. See [[rails/postgres/database-transactions]] for the transaction side of this.

## MVCC Means Readers and Writers Never Block Each Other

Postgres uses MVCC (Multi-Version Concurrency Control). The rule, [verbatim from the docs](https://www.postgresql.org/docs/current/mvcc-intro.html), is "reading never blocks writing and writing never blocks reading."

Concretely, the rule has two halves plus one exception:

- A **plain** `SELECT` never waits for a writer. It returns the last committed value (a snapshot), even while another transaction holds an uncommitted change to that row.
- A writer never waits for a plain reader. It ignores who is reading.
- The **only** pair that blocks is **writer versus writer** on the **same row**.

So a plain `Account.find(42)` issued while another transaction holds row 42 mid-update returns immediately with the old balance. Independent rows proceed fully in parallel.

## Implicit Row Locks Make Writers Block Writers

A bare `UPDATE` or `DELETE` takes an **implicit row-level lock** on the affected row the moment it runs, and holds it until the transaction ends. You do not need `with_lock` or `SELECT FOR UPDATE` for this to happen. A second transaction that tries to `UPDATE` the same row waits until the first commits or rolls back.

This was confirmed by probe. Two transactions both ran `UPDATE accounts SET balance = balance + 100 WHERE id = 42` with no explicit lock anywhere. The first held its transaction open for 3 seconds. The second, starting 1 second in, **blocked for ~2 seconds** until the first committed, then completed. Final balance was 200, both increments correctly applied.

> [Note] The implicit lock is taken at the moment the write statement executes, not when the transaction opens. That timing detail is exactly what makes read-modify-write unsafe (see below).

## Lost Updates and Why with_lock Fixes Them

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

## with_lock, Lock!, and Lock

Rails has three pessimistic-locking APIs. All three emit `SELECT ... FOR UPDATE`, and in all three the lock is held until the **surrounding transaction ends**. The lock duration is identical. They differ in **when and how the lock is acquired**, and in **who owns the transaction**.

Because a row lock lives exactly as long as its transaction, the only question is **who owns the transaction**. `with_lock` opens its own, so it is safe anywhere. `lock!` and `lock` require one you opened. Outside a transaction those two **fail silently**. The SQL runs, the lock is taken and released by auto-commit, and the race is exactly as it was before.

| API | Form | Transaction needed | Why |
| --- | --- | --- | --- |
| `account.lock!` | instance | **yes, yours** | Reloads the row `FOR UPDATE` only. Auto-commit releases the lock the instant the reload returns. |
| `Account.lock.find(42)` | relation | **yes, yours** | The locking `SELECT` *is* the load, but auto-commit still drops the lock right after it. |
| `account.with_lock { }` | instance | **no, it opens one** | Equivalent to `transaction { lock!; yield }`, and joins an existing transaction when nested. |
| `lock_version` | column | **no** | Takes no lock at all. See [Optimistic versus pessimistic locking](#optimistic-versus-pessimistic-locking). |

Note the API shapes differ. `lock!` is the bang method on a loaded record, while `lock` is a query method chained onto a class or relation. There is no `account.lock` on an instance.

```ruby
# (1) with_lock — lock! plus its own transaction wrapper
account.with_lock do
  account.update!(balance: account.balance + 100)
end

# (2) lock! — lock an already-loaded record, inside a transaction you opened
Account.transaction do
  account.lock!
  account.update!(balance: account.balance + 100)
end

# (3) lock (query) — acquire the lock at load time, inside a transaction you opened
Account.transaction do
  account = Account.lock.find(42)
  account.update!(balance: account.balance + 100)
end
```

- **`with_lock(&block)`** wraps the block in a transaction (opening one if needed), reloads the record `FOR UPDATE`, then yields. Self-contained, and the safe default because it **guarantees the transaction boundary exists**.
- **`lock!`** only reloads the already-loaded record `FOR UPDATE`. It does **not** open a transaction. Called outside a transaction it is useless: each statement auto-commits, so the lock is released the instant the reload returns and protects nothing. It is meaningful only **inside a transaction you opened yourself**. It reloads because your earlier plain `SELECT` may now be stale.
- **`lock` (query)** takes the lock at **load time**. `Account.lock.find(42)` issues one `SELECT ... FOR UPDATE` that *is* the load, so the row is locked from the first read with no gap. Also only useful inside a transaction.

Choosing between them:

- Know up front you will write the row: `Account.lock.find` (locked from the first read).
- Already holding an object and *then* decide to lock: `lock!` (reload-and-lock, inside your transaction).
- Want the lock bundled with its own transaction: `with_lock`.

## with_lock Locks One Row, not the Block

`with_lock` locks **only the record it was called on**. Every other row read inside the block is a plain snapshot read, unlocked and possibly stale by the time you write it.

```ruby
# bad: accounts/42 is locked, ledgers/7 is not
account.with_lock do
  ledger = Ledger.find(7)
  ledger.update!(total: ledger.total + 100)   # lost update possible on ledger
end
```

Lock each row you intend to read-modify-write:

```ruby
# good: both rows locked, one transaction (opened by with_lock)
account.with_lock do
  ledger = Ledger.lock.find(7)
  ledger.update!(total: ledger.total + 100)
end
```

This is the payoff of the ownership rule above. `Ledger.lock.find` (or `ledger.lock!`) holds until commit here *because* the enclosing `with_lock` already opened the transaction. The same call at the top level would evaporate.

> [Note] Once a code path takes more than one row lock, acquire them in a **consistent order everywhere**. Locking account-then-ledger in one path and ledger-then-account in another deadlocks; Postgres detects it and aborts one transaction.

## Why a Transaction Does not Speed up Parallel Work

A transaction's purpose is atomicity and isolation, never speed or parallelism. Under contention it generally *hurts* throughput, because it holds every row lock it acquired until commit. The longer a transaction stays open, the longer those locks are held, and the more other writers on those rows are forced to wait.

The way to get parallelism is the opposite of one big transaction:

- Keep transactions **short**, so locks are released quickly.
- Touch **independent rows** where possible, so writers do not contend.
- Rely on MVCC, which already gives parallel reads for free.

Wrapping a large batch job in a single giant transaction does not make it parallel-safe-and-fast. It serializes writers on every contended row and balloons the lock-hold window.

> [Note] Deadlocks arise when two transactions take locks on multiple rows in inconsistent order (A then B versus B then A). Postgres detects them and aborts one transaction. The defense is acquiring locks in a consistent order. See [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html).

## Optimistic Versus Pessimistic Locking

> [Note] The points in this section are practitioner consensus on *when* to choose each strategy, not a hard rule from the docs.

- **Pessimistic locking** (`with_lock` / `SELECT FOR UPDATE`) blocks competing writers up front. It wins for **write-heavy, high-conflict** rows, where retries would mostly be wasted. The cost is reduced concurrency on the locked row.
- **Optimistic locking** (Rails' `lock_version` column) lets writers proceed without locking and raises `StaleObjectError` if two writers collide, leaving you to retry. It wins for **read-heavy, low-conflict** data, where collisions are rare and retries are cheap.

Optimistic locking also takes **no lock call**. Neither `lock!` nor `lock` is involved, and there is no instance-level `lock` method to reach for anyway. Adding the `lock_version` column is what activates the check.

### How an Optimistic Collision Plays Out

Both requests load account 42 while `lock_version` is 3.

```ruby
# request A                       request B
a = Account.find(42)              b = Account.find(42)   # both read lock_version 3
a.balance = 100
                                  b.balance = 200
a.save!
# UPDATE accounts SET balance = 100, lock_version = 4
#   WHERE id = 42 AND lock_version = 3   -> 1 row, commits
                                  b.save!
                                  # UPDATE accounts SET balance = 200, lock_version = 4
                                  #   WHERE id = 42 AND lock_version = 3   -> 0 rows
                                  # => ActiveRecord::StaleObjectError
```

The **second write** fails, never the first. Ordering is by write time rather than read time, so whichever `save!` lands first wins even if it loaded the record second. Only a *committed* first write causes the failure. If A rolls back, `lock_version` returns to 3, B's condition matches again on re-evaluation, and B succeeds.

Compare the three outcomes for that second writer. Optimistic locking fails it fast with `StaleObjectError` and leaves you to retry. Pessimistic locking makes it wait, then proceed on fresh data. No locking at all lets it silently overwrite the first, which is the lost update above.

### Optimistic Locking Needs No Transaction

Optimistic locking needs **no transaction**, unlike `lock!` and `lock`. It takes no lock to hold open. Rails appends `WHERE lock_version = N` to the `UPDATE` and raises `StaleObjectError` when zero rows match. The check and the write are a single atomic statement. A transaction is only useful around the surrounding read-compute-retry cycle, never to make the version check work.

Both are valid. Choose by the conflict rate on the data, not by habit.

## Advisory Locks Lock a Name, Not a Row

An advisory lock claims an **integer**, not a row. Postgres keeps a server-wide registry of which connection currently holds which number. There is no table, no row, and no relationship to your data. That is what "advisory" means. Postgres offers no opinion about what the number stands for and will not stop anyone from writing the rows you believe it protects. The only guarantee is that while you hold a number, nobody else can hold it. The meaning is a convention shared by the callers that agree on the same name.

Underneath it is two function calls.

```sql
SELECT pg_try_advisory_lock(12345);   -- t = acquired, f = held by another session
SELECT pg_advisory_unlock(12345);
```

The [with_advisory_lock gem](https://github.com/ClosureTree/with_advisory_lock) hashes a string into that integer, runs the block once it holds the lock, and releases it in an `ensure` so an exception cannot leak it.

```ruby
Component.with_advisory_lock("pull_component_42", timeout_seconds: 0) do
  since = sync_state.last_successful_sync_at
  records = Api.fetch(updated_since: since)    # network call, no transaction open

  Component.transaction do                     # short, and touches no network
    records.each { |r| Component.upsert(r.attributes, unique_by: :remote_id) }
    sync_state.update!(last_successful_sync_at: records.map(&:updated_at).max)
  end
end
```

Calling it on a model is only how you reach a database connection. It locks the **string**, not the `components` table, so `Thing.with_advisory_lock("pull_component_42")` would exclude the block above just as effectively.

Two properties make this the right tool when a critical section has to span a network call.

- The lock is **session-scoped rather than transaction-scoped**. It can wrap the HTTP request while the transaction stays short and touches no network. A row lock cannot do this, because it dies with its transaction.
- The lock is **held by the connection rather than stored as data**. If the worker is killed, the connection drops and Postgres releases the lock immediately. The homemade equivalent, a `syncing: true` column, stays stuck true forever after a crash and needs timeout logic to guess whether the holder is still alive.

### Choosing timeout_seconds

`timeout_seconds` decides what the caller that loses the race does.

- **`0`** attempts the lock once and gives up, so the block never runs and the call returns `false`. This is the `pg_try_advisory_lock` path. It is the right choice for a periodic sync, where waiting only to redo work the holder is already doing is pure waste. Handling the falsy return is the caller's job.
- **A positive value** waits up to that many seconds for the holder to finish and then runs the block. Use it when the loser's work is *not* redundant, for example when each caller carries a different payload that must not be dropped.
- **Waiting indefinitely** turns a single hung holder into a growing pile of blocked workers, so avoid it inside jobs. Confirm the default in the gem version you use rather than assuming, since the blocking and non-blocking paths behave very differently.

> [Note] A hung holder starves every other caller silently, with no exception raised anywhere. An advisory lock therefore makes an explicit HTTP timeout mandatory rather than optional, because that timeout is the only bound on how long the others keep being turned away.

Two caveats limit where advisory locks apply.

- They are **per database server**, so they only exclude callers connected to the same Postgres. An advisory lock is not a distributed lock across separate databases.
- **Session-level advisory locks are unsafe under PgBouncer in transaction pooling mode**, because consecutive statements can land on different backend connections and the unlock may never reach the connection holding the lock. Use `pg_advisory_xact_lock` there, which is transaction-scoped and released at commit. That reintroduces exactly the transaction coupling an advisory lock was meant to escape.

## Related Concepts

- [[rails/postgres/database-transactions]]: atomicity, isolation levels, rollback semantics, and when to use a transaction.
- [[rails/postgres/upsert-and-concurrent-inserts]]: handling concurrent inserts and the race conditions unique constraints catch.

## References

- [PostgreSQL: Introduction to MVCC](https://www.postgresql.org/docs/current/mvcc-intro.html): "reading never blocks writing and writing never blocks reading."
- [PostgreSQL: Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html): row locks, `FOR UPDATE`, writer-blocks-writer, deadlock detection.
- [Rails API: ActiveRecord::Locking](https://api.rubyonrails.org/classes/ActiveRecord/Locking/Pessimistic.html): `with_lock` and `lock!` pessimistic locking.
- [PostgreSQL: Advisory Locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS): session versus transaction scope, `pg_try_advisory_lock`, automatic release when the session ends.
- [with_advisory_lock gem](https://github.com/ClosureTree/with_advisory_lock): the Ruby wrapper, lock naming, and `timeout_seconds`.

**Practitioner / opinion:**

- [Implement optimistic locking in Rails](https://blog.kiprosh.com/implement-optimistic-locking-in-rails/): optimistic versus pessimistic tradeoffs.
