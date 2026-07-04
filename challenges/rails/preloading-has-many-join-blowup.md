---
wiki: rails/activerecord-preloading
section: "Cost model: when JOIN multiplies rows"
kind: predict-output
env: pg
questions:
- With 1000 users averaging 50 posts each, how many rows cross the wire under eager_load versus preload's two queries?
- Why does bob still appear in the result even though he has no posts?
created: 2026-07-03
---

## Brief

Two users, one with three posts and one with none. Predict every row the LEFT OUTER JOIN returns. This is the exact result shape eager_load reconstructs objects from.

## Setup

```sql
CREATE TABLE users (id int PRIMARY KEY, name text);
CREATE TABLE posts (id int PRIMARY KEY, user_id int, title text);
INSERT INTO users VALUES (1, 'alice'), (2, 'bob');
INSERT INTO posts VALUES (1, 1, 'p1'), (2, 1, 'p2'), (3, 1, 'p3');
```

## Stub

```sql
SELECT users.name, posts.title
FROM users
LEFT OUTER JOIN posts ON posts.user_id = users.id
ORDER BY users.id, posts.id;
```

## Solution

```sql
SELECT users.name, posts.title
FROM users
LEFT OUTER JOIN posts ON posts.user_id = users.id
ORDER BY users.id, posts.id;
```

## Expected Output

```
PLACEHOLDER
```
