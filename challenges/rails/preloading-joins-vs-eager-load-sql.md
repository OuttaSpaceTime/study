---
wiki: rails/activerecord-preloading
section: The four methods
kind: predict-output
env: rails
questions:
- Why does iterating user.posts after a joins query still fire N+1 queries?
- What are the t0_r0 style column aliases in the eager_load SELECT used for?
created: 2026-07-03
---

## Brief

Two temp tables, one has_many. Predict the SQL each method generates, paying attention to which columns each SELECT pulls.

## Stub

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

puts User.joins(:posts).to_sql
puts User.eager_load(:posts).to_sql
```

## Solution

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

puts User.joins(:posts).to_sql
puts User.eager_load(:posts).to_sql
```

## Expected Output

```
PLACEHOLDER
```
