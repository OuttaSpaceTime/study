---
wiki: rails/activerecord-preloading
section: Choosing between joins, preload, eager_load, and includes
kind: write-code
env: rails
questions:
- Why combine joins with preload here instead of reaching for eager_load?
- Why is distinct needed once you INNER JOIN a has_many?
created: 2026-07-03
---

## Brief

Build the relation that filters users by a child condition via INNER JOIN while loading the posts in a separate query. This is the combo for cross-table filtering without row-multiplying the fetch.

## Stub

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id; t.boolean :published }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

# TODO: only users with at least one published post, each appearing once,
# with posts loaded for later access but not fetched through the JOIN
relation = User.all

puts relation.to_sql
puts relation.preload_values.inspect
```

## Solution

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id; t.boolean :published }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

relation = User.joins(:posts).where(posts: { published: true }).distinct.preload(:posts)

puts relation.to_sql
puts relation.preload_values.inspect
```

## Expected Output

```
PLACEHOLDER
```
