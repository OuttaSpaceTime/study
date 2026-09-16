---
title: Indexes
aliases:
- database index
- B-tree index
- index scan
- how indexes work
- EXPLAIN ANALYZE index
tags:
- sql
- postgres
- indexes
- performance
created: '2026-09-16'
updated: '2026-09-16'
source_skill: study-walkthrough
flashcard_ids:
- cmu3pa20k0000jz1arq8stgy7
- cmu3pa33h0001jz1a12j5ecy2
- cmu3pa4ao0002jz1ahgda4jd7
- cmu3pa5l20003jz1a5xz22vd1
- cmu3pa6j90004jz1aroj8hqdr
---

# Indexes

## TL;DR

A database index is a separate, sorted data structure that holds an indexed column's values plus a pointer back to the row. It is not a copy of the table, and the table itself keeps only one physical order. Postgres defaults to a B-Tree index, which narrows a search by roughly 100x per level because each node holds enough keys to fill one disk page. That gives lookup cost that grows logarithmically with table size, while a full table scan grows linearly. Most index lookups still cost one extra trip back to the table (a heap fetch) to read columns that are not in the index; a query answerable from the index alone skips that trip entirely (an index-only scan).

## What an Index Actually Is

A table can only be physically stored in one order. Adding an index on `email` and a separate index on `created_at` cannot both sort the table itself, since a table row only has one position on disk. Each index instead lives in its own structure, sorted by its own column, holding just that column's value plus a pointer (row id) back to the actual row. This is why you can have many indexes on one table, each optimized for a different lookup, without conflicting with each other or with the table's own storage order.

## Heap Fetch vs Index-Only Scan

Because an index entry stores only the indexed column and a pointer, most queries need a second step. That step follows the pointer back to the table page, often called the heap, to read any column that is not in the index. This second trip is called a heap fetch.

If every column a query asks for is already present in the index, Postgres can skip the heap fetch entirely. That is an index-only scan. For example, `SELECT email, id FROM users WHERE email = 'x@example.com'` can be satisfied from an `email` index alone, but `SELECT * FROM users WHERE email = 'x@example.com'` needs the heap fetch, since `status` and `created_at` are not stored in that index.

## Sequential Scan: Cost Scales Linearly with Table Size

Without a usable index, Postgres falls back to a sequential scan. It reads every row in physical order and checks each one against the `WHERE` clause. On a 500,000-row `users` table with no index on `email`, `EXPLAIN ANALYZE` for `WHERE email = 'user250000@example.com'` produced:

```
Gather (actual time=7.788..15.733 rows=1 loops=1)
  Workers Planned: 2
  Workers Launched: 2
  -> Parallel Seq Scan on users (actual time=8.879..10.549 rows=0.33 loops=3)
       Filter: (email = 'user250000@example.com'::text)
       Rows Removed by Filter: 166666
Execution Time: 15.799 ms
```

`loops=3` is the leader plus two parallel workers splitting the table into three chunks of about 166,666 rows each. Parallelism cuts wall-clock time, but the total work done, and the cost, still scales with the table's row count. Doubling the table roughly doubles the scan time, no matter how many workers help.

## B-Tree Structure: Why Height Grows so Slowly

A B-Tree generalizes binary search from one key with two children to n keys with n+1 children per node. A node with 3 sorted keys needs 4 child pointers, one for each of the four ranges those keys create (below the first key, between each pair, and above the last one).

Real B-Tree nodes are sized to fill one disk page (8KB in Postgres), so a node can hold on the order of 100 keys, not 3. That means each level of the tree narrows the search space by roughly 100x. Going from 500,000 candidate rows to a single match takes about 3 levels, since 500,000 / 100 / 100 / 100 is already below 1. This is why B-Tree lookup cost grows logarithmically with table size instead of linearly like a sequential scan.

## Reading EXPLAIN ANALYZE: Buffers, Pages, and Scan Types

Postgres stores tables and indexes as sequences of fixed-size pages (8KB by default), and reads or writes a full page at a time even to fetch one row or key. The `Buffers` line in `EXPLAIN (ANALYZE, BUFFERS)` output counts page touches. `shared hit` means the page was already in Postgres's in-memory cache; `read` means it had to come from disk (or the OS cache).

After creating `CREATE INDEX idx_users_email ON users(email)`, the same query changed plan and cost:

```
Index Scan using idx_users_email on users (actual time=0.015..0.016 rows=1 loops=1)
  Index Cond: (email = 'user250000@example.com'::text)
  Buffers: shared hit=1 read=3
Execution Time: 0.042 ms
```

Postgres labels this node `Index Scan`, not a `B-Tree scan`. B-Tree is the index's internal structure; `Index Scan` is the plan operation that walks it. Execution time dropped from 15.799 ms to 0.042 ms, and buffer touches dropped from 4,673 to 4. Of those 4 touches, about 3 correspond to walking the tree's levels to find the matching pointer, and the 4th is the heap fetch that reads the actual row for the columns `SELECT *` needs beyond `email`.

## Related Concepts

- [[sql/nullable-columns]]: partial unique indexes narrow an index to a subset of rows matching a `WHERE` predicate, a related but distinct technique from the plain B-Tree index covered here.
- [[rails/postgres/foreign-keys]]: a foreign key constraint does not automatically create an index on the referencing column, so lookups and cascades on an unindexed FK column fall back to a sequential scan.

## References

- [PostgreSQL: Index Types](https://www.postgresql.org/docs/current/indexes-types.html): B-Tree as the default index type, and what operations it supports.
- [PostgreSQL: Index-Only Scans](https://www.postgresql.org/docs/current/indexes-index-only-scans.html): when a query can be answered from the index alone, skipping the heap fetch.
