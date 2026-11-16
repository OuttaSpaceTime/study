---
title: Database Normalization
aliases:
- normalization
- normal forms
- 3nf
- denormalization
- database normal forms
tags:
- sql
- database
- normalization
- schema-design
- data-modeling
created: '2026-11-11'
updated: '2026-11-11'
source_skill: study-walkthrough
flashcard_ids:
- cmwbt5fbd0000s71a7jyinisa
- cmwbt71xv0007s71a6l62ui7k
- cmwbt5p6f0001s71a651ufxgw
- cmwbt5wc20002s71af01hvnvw
- cmwbt61ch0003s71arhwf3nua
- cmwbt66fq0004s71a40z3wy5u
- cmwbt75tl0008s71ad7ze1s4c
- cmwbt6gdr0005s71aqj148np3
- cmwivw1h90000kr1ach8cjiuq
- cmwivw64b0001kr1as2ai25ab
- cmwivweyv0002kr1a6rcd9hg3
- cmwbt7a940009s71anct4wrbh
- cmwbt6spw0006s71acdh1hcu4
- cmwiyboih00004q1ajmf134so
- cmwiyc0pp00014q1aney5ms4x
explorables:
- https://claude.ai/artifact/SpWnxwZAjPCj3XMH3nbE82
---

# Database Normalization

## TL;DR

Normalizing a schema means storing each fact in exactly one place, so the database cannot hold two versions of it. The practical target is third normal form (3NF). Constraints in the schema do the enforcing, and a copy is a deliberate exception you can name as a snapshot or a cache. Any other copy is a bug waiting for an update that misses one row.

## What Normalization Is

Column B is **functionally dependent** on column A when any two rows with the same value of A must have the same value of B. `customer_email` depends on `customer_id`. Normal forms are rules about which dependencies a table may contain.

A wide table that mixes facts about different things shows three anomalies.

- **Update anomaly**: one fact is stored on many rows and an edit misses some. A customer's email sits on all their orders, and only one row gets the new value.
- **Insert anomaly**: a fact has no row to live in until an unrelated fact exists. A customer cannot be stored before their first order.
- **Delete anomaly**: removing one fact erases another. Deleting a customer's last order deletes the customer.

All three have one cause. Each row holds two kinds of fact at once. The fix is one table per kind of fact.

## The Normal Forms in Practice

To normalize, ask what decides the value of each non-key column. If the whole key decides it, the column stays. If part of the key or another non-key column decides it, the column moves to a table keyed by whatever decides it.

| Form | A column must depend on | Typical violation | Fix |
| --- | --- | --- | --- |
| 1NF | One value per cell, no repeating groups | `phone1`, `phone2`, `phone3` columns | A child table with a foreign key |
| 2NF | The whole key, not part of it | `product_name` on `order_lines(order_id, product_id, ...)` | A `products` table keyed by `product_id` |
| 3NF | The key, and no other non-key column | `advisor_room` on `students(student_id, advisor, ...)` | An `advisors` table keyed by `advisor` |

"The key, the whole key, and nothing but the key" names 1NF, 2NF and 3NF in that order. Strictly, 2NF and 3NF apply to every candidate key, not only the primary key. A table whose only candidate key is one column has no partial dependencies, so it cannot break 2NF.

Splitting `order_lines(order_id, product_id, qty, order_date, customer_id, customer_email, product_name)` this way gives four tables.

```sql
order_lines(order_id, product_id, qty)         -- qty needs the whole key
orders(order_id, order_date, customer_id)      -- order_date and customer_id need only order_id
products(product_id, product_name)             -- product_name needs only product_id
customers(customer_id, customer_email)         -- customer_email needs only customer_id
```

Boyce-Codd normal form (BCNF) is stricter. Every nontrivial dependency must start from a superkey. It differs from 3NF only when candidate keys overlap, and decomposing to BCNF can lose the ability to enforce some dependencies ([Wikipedia](https://en.wikipedia.org/wiki/Boyce%E2%80%93Codd_normal_form)). Microsoft's guide calls 3NF the highest level necessary for most applications. 4NF and 5NF are rarely considered in practice.

## The Schema Is the Guard

Splitting the tables removes the copies. Constraints stop writes that would break the structure again, on every write and from every code path.

- `FOREIGN KEY`: every `orders.customer_id` must exist in `customers`. `ON DELETE` picks what happens to children. `NO ACTION` (the default) rejects the delete. `CASCADE` deletes the children, which is consistent but erases data. `SET NULL` keeps them without an owner.
- `UNIQUE`: no two rows share a value, and Postgres creates an index to enforce it. NULLs are not equal to each other unless you ask ([[sql/nullable-columns]]).
- `NOT NULL`: the column must have a value.
- `CHECK`: a rule over one row. It cannot look at other rows or tables.

An app validation runs only when a write goes through the model. Scripts, `insert_all`, `delete_all`, raw SQL and other services skip it. The kind of check also matters.

- A check that reads only the record, such as presence, is safe in the app. Its answer cannot go stale.
- A check that reads other rows, such as uniqueness, races. Two concurrent requests both look for the email, both find nothing, and both insert. Only a unique constraint, checked at the moment of the insert, closes the gap.

Keep the app validations for friendly error messages and let the schema be the guard. See [[rails/postgres/foreign-keys]] for foreign keys in Rails.

## What Normalization Costs

Showing data that moved to another table takes a lookup. Two costs matter in everyday code.

- **N+1 queries**: looping over 10 orders and reading `order.customer.name` sends 1 query for the orders and 10 for the customers. `includes(:customer)` makes it 2, and `eager_load(:customer)` makes it 1 with a `LEFT OUTER JOIN`. N+1 is an app loading pattern. It does not mean the join is slow, so check the query log before blaming the schema.
- **Unindexed foreign keys**: Postgres does not index the referencing column of a foreign key. `WHERE customer_id = 1` on a large `orders` table then scans every row, and so does each `DELETE` on `customers`, which must look for orders that still point at it. `t.references` adds the index in a Rails migration, but `add_foreign_key` alone adds only the constraint. See [[sql/indexes]].

A join on an indexed key is cheap. Slow pages usually come from round trips or a missing index, and copying the column into the other table fixes neither's root cause while bringing back the update anomaly.

## When a Copy Is the Right Answer

Normalized does not mean copy-free. Sort each copy by what it is.

| Kind | Example | Why it is fine or not |
| --- | --- | --- |
| Snapshot | `order_lines.unit_price`, `orders.shipping_address` | It records a moment. A join to today's price would rewrite last month's invoices. |
| Cache | `customers.orders_count`, a nightly `revenue_by_month` table | Derived from other data, and fine while every write path keeps it true or its staleness is accepted. |
| Bug | `orders.customer_email` copied from `customers` | A live fact with a second home. This is the update anomaly again. |

A counter kept by an `after_create` callback drifts when a write skips callbacks. `insert_all` adds orders without raising the count, and `delete_all` removes orders without lowering it. Nothing errors, and the admin list sorts by a wrong number. A counter you care about needs a database trigger or a periodic recount.

Keep a copy when it records a moment, or when you own every write path and have measured the read it saves. Otherwise leave it out.

## Tradeoffs & Gotchas

- Practitioners mostly agree on one default. Start fully normalized, and denormalize only for a measured bottleneck. Premature denormalization adds maintenance cost with no demonstrated benefit. Label: consensus.
- Practitioners also separate denormalizing for speed from snapshotting for correctness. The first is an optimization to measure. The second is a modeling decision and is part of a correct design. Label: single voice, but it matches the Postgres and Microsoft material above.
- Copies diverge when one write path is missed. A counter trigger that handles INSERT and DELETE but not UPDATE is a common case. Materialized views are stale until refreshed. Label: consensus.
- Try an index or a query fix before denormalizing. Label: consensus.
- A `jsonb` column suits fluid, variable attributes. It enforces no structure, any update locks the whole row, and a B-tree index on it only helps whole-document equality. Keep documents small and keep what you always query, constrain or join on in real columns.
- A vendor claim says columnar analytics engines make runtime joins cheap, so normalization works even for analytics. It is about OLAP engines and not about transactional Postgres or MySQL, so do not apply it to everyday app code. Label: single voice.
- Microsoft's guide warns that many small tables may hurt performance. That advice dates from Access-era limits, and indexed joins on a modern server are cheap. The underlying point still stands. 3NF is a default and not a law.

## Related Concepts

- [[sql/nullable-columns]]: `UNIQUE` and `NOT NULL` behave differently around NULL, which matters for the constraints above.
- [[rails/postgres/foreign-keys]]: `on_delete` options and deferrable constraints in Rails.
- [[sql/indexes]]: why an unindexed foreign key column falls back to a sequential scan.
- [[rails/postgres/database-transactions]]: the other way concurrent writes interact with constraints.

## References

- [Microsoft Learn, Description of the database normalization basics](https://learn.microsoft.com/en-us/office/troubleshoot/access/database-normalization-description): 1NF to 3NF in plain terms, with the anomaly examples.
- [PostgreSQL, Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html): foreign keys, `ON DELETE`, `UNIQUE` and `CHECK`, and the note that foreign keys do not create an index on the referencing column.
- [PostgreSQL, JSON types](https://www.postgresql.org/docs/current/datatype-json.html): when a document column fits, row locking on update, and GIN indexes.
- [Rails Guides, Active Record Query Interface](https://guides.rubyonrails.org/active_record_querying.html): N+1 queries and `includes`, `preload` and `eager_load`.

**Practitioner / opinion:**

- [kindatechnical, When to denormalize](https://kindatechnical.com/postgresql/when-to-denormalize-performance-vs-integrity-trade-offs.html): normalize first, and snapshots as a correctness choice.
- [ClickHouse, When to denormalize and when to join](https://clickhouse.com/resources/engineering/when-to-denormalize-when-to-join): the columnar-engine view, which is a vendor claim.
