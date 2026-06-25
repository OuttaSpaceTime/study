---
title: ActiveRecord preloading
aliases:
- activerecord preloading
- preload vs eager_load vs includes
- includes vs preload
- n+1 prevention rails
- association preloading
tags:
- rails
- activerecord
- performance
- n-plus-one
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
flashcard_ids:
- cmosqcwsg0000h30mvfne2v51
- cmosqd3r80001h30mwd2tbpht
probe_sections:
- The four methods
- How includes auto-switches
- 'Cost model: when JOIN multiplies rows'
- Choosing between joins, preload, eager_load, and includes
- Polymorphic associations
last_probed:
- Choosing between joins, preload, eager_load, and includes
- Polymorphic associations
- The four methods
- How includes auto-switches
- 'Cost model: when JOIN multiplies rows'
review_interval: 45
next_review: '2026-07-23'
---

# ActiveRecord preloading: joins, preload, eager_load, includes


ActiveRecord offers four methods that interact with associations in a query. `joins`, `preload`, `eager_load`, and `includes` look interchangeable at first, but they aren't. The choice between them controls how many SQL queries fire, how rows multiply over the wire, and whether the WHERE clause can filter on associated tables. Picking wrong is a common source of N+1 queries *and* of accidental Cartesian-style row blowup.

## TL;DR

| Method | Query shape | Preloads? | Filters on assoc? | Use when |
|---|---|---|---|---|
| `joins` | `INNER JOIN` | **No** | Yes | You need an INNER JOIN for filtering/ordering, and you don't need the assoc loaded |
| `preload` | 2 separate queries | Yes | No (cannot reference) | Default for `has_many` preloading. Safe under any cardinality. |
| `eager_load` | 1 `LEFT OUTER JOIN` | Yes | Yes | `belongs_to` / `has_one`, or when you must filter parents by child conditions |
| `includes` | Either of the above | Yes | Yes | Convenient default. The auto-switch is what trips people. |

**Default heuristic:** reach for `preload`. Switch to `eager_load` when (a) the association is `belongs_to` / `has_one`, or (b) you genuinely need to filter parents by child conditions. Treat `includes` as a tool you understand the auto-switch rule of, not as a magic safe choice.

## The four methods

### `joins`: INNER JOIN, no preloading

```ruby
User.joins(:posts)
# SELECT users.* FROM users INNER JOIN posts ON posts.user_id = users.id
```

Records are **not** preloaded. Iterating `user.posts` after this fires a fresh N+1. `joins` is for filtering or ordering by the joined table. Use this when you need the JOIN in scope of a single SQL statement but don't actually need the associated objects in memory.

INNER JOIN means parents without children are excluded from the result. Use this when that's what you want; otherwise prefer `eager_load` (LEFT OUTER) or combine `joins` with an explicit `preload`.

### `preload`: bulk-load via separate queries

```ruby
User.preload(:posts).to_a
# SELECT users.* FROM users
# SELECT posts.* FROM posts WHERE posts.user_id IN (1, 2, ..., N)
```

Two queries, no row blowup. The IN list grows linearly with the parent count. The associated records are attached to the parent objects in memory; subsequent `user.posts` access is free.

Cannot be combined with WHERE clauses that reference the joined table. There's no joined table in either statement. Trying to do so raises an error or silently fails to apply the filter.

### `eager_load`: single LEFT OUTER JOIN

```ruby
User.eager_load(:posts).to_a
# SELECT users.id  AS t0_r0, ..., posts.id AS t1_r0, posts.user_id AS t1_r1, ...
# FROM users LEFT OUTER JOIN posts ON posts.user_id = users.id
```

One query, all data in one round trip. Aliased columns (`t0_*` for parents, `t1_*` for children) let Rails reconstruct the object graph from a flat result set. The dedup key is the parent's primary key (conventionally `t0_r0`). Duplicate parent rows collapse into one in-memory parent during processing.

Filters on the joined table work directly. `eager_load(:posts).where(posts: { published: true })` is a single SQL statement.

### `includes`: auto-switches between preload and eager_load

```ruby
User.includes(:posts).to_a
# 2 queries (acts like preload)

User.includes(:posts).where(posts: { published: true }).to_a
# 1 LEFT OUTER JOIN (acts like eager_load)
```

`includes` is a **strategy-deciding** method. It defaults to `preload` semantics and upgrades to `eager_load` semantics when the query would be impossible to satisfy as two separate statements.

## How includes auto-switches

The trigger is purely structural. **Does the query need the associated table in scope?**

`includes` upgrades to a single LEFT OUTER JOIN when **any** of these is true:

- WHERE / ORDER references the joined table by name in a string SQL fragment (e.g., `where("posts.title LIKE ?", "%rails%")`)
- WHERE uses hash form keyed by the association name: `where(posts: { published: true })`: Rails's predicate builder auto-references the table when the hash key is an association.
- `.references(:posts)` is called explicitly.

Pure parent-table conditions leave it as two queries:

```ruby
User.includes(:posts).where(name: "Felix").to_a   # 2 queries (preload)
User.includes(:posts).where(posts: { id: 1 })     # 1 JOIN (eager_load)
```

The "magic" framing (`includes` "decides for you") is misleading. The behavior is mechanical. If the WHERE/ORDER needs the join, you get a JOIN; otherwise you get two queries.

## Cost model: when JOIN multiplies rows

The fundamental cost difference between `preload` and `eager_load` comes from JOIN cardinality.

### `has_many` JOIN: row blowup

`User.eager_load(:posts).to_a` with 1,000 users averaging 50 posts each → **50,000 rows over the wire**, each carrying every `users.*` column duplicated. The blowup is `parents × avg_children`, and the duplication penalty is `parent_column_count × (avg_children − 1)` extra cells per parent.

The `preload` equivalent. 1,000 user rows + 50,000 post rows = 51,000 total. Each row appears once.

Wire cost ratio scales with parent column width and children-per-parent. For wide parent tables and high `has_many` fan-out, `preload` is dramatically cheaper.

### `belongs_to` JOIN: no row blowup

`Post.eager_load(:author).to_a` with 10,000 posts and 5 distinct authors → **10,000 rows**. Same row count as `Post.all`. The JOIN doesn't multiply row count from the post side; it just attaches author columns to each post row. The duplication is on the *parent* (author) side. Alice's 5 columns are copy-pasted across every post she wrote.

Wire cost is `posts × (post_cols + author_cols)`. Compare to preload's `posts × post_cols + 5 × author_cols`. The differential is small unless the parent table is much wider than the child table.

This is why `belongs_to` / `has_one` JOINs are usually fine. They don't trigger row blowup.

### Memory after instantiation: identical

Persistent ActiveRecord objects are the same in both strategies. Rails dedupes parents by `t0_r0` (primary key) during result-set traversal. Duplicate rows produce one parent object, not many.

What's larger for `eager_load`:
- **Transient memory** during result processing. Driver buffers full result set.
- **Allocation churn.** Duplicate column strings are allocated and become garbage immediately. On large `has_many` JOINs this GC pressure can dominate end-to-end time even when wire cost is acceptable.

### Round trips vs cell volume

`preload` pays 2 round trips; `eager_load` pays 1. On low-latency LAN connections, RTT is negligible and cell volume dominates → `preload` wins for `has_many`. On high-latency WAN connections, RTT can swamp the duplication cost → `eager_load` can win even for `has_many`. The tradeoff is **cell volume vs round trips**, not "preload is always faster."

## Choosing between joins, preload, eager_load, and includes

| Situation                                                | Choice                                                  | Reason                                            |
| -------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------- |
| `has_many`, no cross-table filter                        | `preload`                                               | Avoids row blowup                                 |
| `has_many`, must filter parents by child conditions      | `eager_load` (or `includes` + WHERE on assoc)           | The JOIN is mandatory. Can't express otherwise   |
| `belongs_to` / `has_one`, no filter                      | Either. `eager_load` saves 1 RTT, no row blowup.        | JOIN cardinality stays at parent count            |
| `belongs_to` / `has_one`, filter on parent               | `eager_load`                                            | Same. Trivially supports the filter.             |
| Need INNER JOIN for filtering, don't need objects loaded | `joins`                                                 | Skip the preload overhead entirely.               |
| Want INNER JOIN *and* preloaded objects                  | `joins` + `preload`                                     | Combine filter via JOIN with load via separate query |
| Mixed needs across many call sites                       | Default to `preload`. Reach for others only with reason.| Hardest to footgun.                               |

The common "mainly use `preload`" advice is correct *for `has_many`* but oversimplified for `belongs_to`. The rule is to avoid `eager_load` when it would multiply rows. This is `has_many`-specific.

## Polymorphic associations

`eager_load` cannot JOIN a polymorphic `belongs_to`. The associated table is unknown at SQL build time: `entry.entryable` could be a `Message` or a `Comment`, and a single JOIN can't union arbitrary tables. So:

```ruby
Entry.eager_load(:entryable)   # raises ActiveRecord::EagerLoadPolymorphicError
Entry.includes(:entryable)     # works — runs one query per distinct entryable_type
Entry.preload(:entryable)      # works — same shape as includes here
```

`preload` (and `includes` defaulting to preload) handles polymorphism by issuing one extra query per distinct subtype found in the parent set. It issues one query for messages, one for comments, etc. See [[rails/delegated-type]] for a worked example with the `entryable` polymorphic association.

You also can't filter polymorphic associations cross-table. `where(entryable: { ... })` is meaningless because the column set isn't shared. To filter by subtype-specific conditions, narrow with the type scope first using `entries.messages.includes(:entryable)`.

## Related Concepts

- [[rails/delegated-type]]: polymorphic `belongs_to :entryable` with `includes` for N+1 prevention; concrete example of the polymorphic case discussed here.
