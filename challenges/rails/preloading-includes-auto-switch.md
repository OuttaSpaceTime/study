---
wiki: rails/activerecord-preloading
section: How includes auto-switches
kind: predict-output
env: rails
questions:
- What structural condition makes includes upgrade from two queries to a single LEFT OUTER JOIN?
- Why does the where(name:) condition leave includes in preload mode?
created: 2026-07-03
---

## Brief

Same includes call, two different WHERE clauses. Predict which one prints a plain parent query and which one prints a JOIN.

## Stub

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id; t.boolean :published }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

puts User.includes(:posts).where(name: "Felix").to_sql
puts User.includes(:posts).where(posts: { published: true }).to_sql
```

## Solution

```ruby
ActiveRecord::Base.connection.create_table(:users, temporary: true) { |t| t.string :name }
ActiveRecord::Base.connection.create_table(:posts, temporary: true) { |t| t.integer :user_id; t.boolean :published }
class User < ActiveRecord::Base; has_many :posts; end
class Post < ActiveRecord::Base; belongs_to :user; end

puts User.includes(:posts).where(name: "Felix").to_sql
puts User.includes(:posts).where(posts: { published: true }).to_sql
```

## Expected Output

```
PLACEHOLDER
```
