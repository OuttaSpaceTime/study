---
topic: activerecord-preloading
session: 2026-05-05-walkthrough
wiki: rails/activerecord-preloading
created: 2026-05-05 12:30
---

## Prediction

`User.includes(:memberships).where(memberships: { role: :admin })` would emit two
queries (preload), because the WHERE is hash-form rather than a string SQL
fragment. The contrast case `where(email: 'x')` would also emit two — same
shape, just filtering on the parent table.

## Command

```ruby
# In a real Rails console (vilocifyportal)
ActiveRecord::Base.logger = Logger.new(STDOUT)

# Case A — hash WHERE keyed by association name
User.includes(:memberships).where(memberships: { role: :admin }).to_a

# Case B — WHERE on parent table only
User.includes(:memberships).where(email: 'accepted@example.com').to_a
```

## Output

```
# Case A — ONE query, LEFT OUTER JOIN
User Eager Load (2.9ms)  SELECT "users"."id" AS t0_r0, ...,
  "memberships"."id" AS t1_r0, ...
  FROM "users"
  LEFT OUTER JOIN "memberships"
    ON "memberships"."organization_id" IS NULL
   AND "memberships"."user_id" = "users"."id"
  WHERE "memberships"."role" = 'admin'

# Case B — TWO queries (preload)
User Load (1.3ms)  SELECT "users".* FROM "users"
  WHERE "users"."email" = 'accepted@example.com'
Membership Load (0.9ms)  SELECT "memberships".* FROM "memberships"
  WHERE "memberships"."organization_id" IS NULL
    AND "memberships"."user_id" = 971237205
```

## Takeaway

Prediction was wrong on Case A. `includes` upgrades to a single LEFT OUTER JOIN
whenever the WHERE references the joined table — and **hash-form**
`where(memberships: { … })` counts as a reference, not just string SQL like
`where("memberships.role = ?", …)`. Rails's predicate builder sees the
association name as the hash key and auto-references the table.

Trigger rule: **does the WHERE need the joined table to be present in scope?**
- Yes → single JOIN (eager_load semantics)
- No → two queries (preload semantics)

Bonus: the JOIN's `ON` clause carried `organization_id IS NULL` from the
association scope on `User has_many :memberships`. Eager-loaded JOINs inherit
whatever conditions the association definition adds.
