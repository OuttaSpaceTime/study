---
wiki: rails/routing/shallow-routing
section: Named Helpers Change Too
kind: write-code
env: rails
questions:
- How do the helper name and its arguments change when a route goes shallow?
- Which helper would you call for the new comment form, and what argument does it take?
created: 2026-07-03
---

## Brief

The collection helper keeps the parent prefix and takes the post. Write the matching member helper call for a single comment's show path.

## Stub

```ruby
Rails.application.routes.draw do
  resources :posts do
    resources :comments, shallow: true
  end
end

helpers = Rails.application.routes.url_helpers
puts helpers.post_comments_path(1)
# TODO: print the show path for the comment with id 5
```

## Solution

```ruby
Rails.application.routes.draw do
  resources :posts do
    resources :comments, shallow: true
  end
end

helpers = Rails.application.routes.url_helpers
puts helpers.post_comments_path(1)
puts helpers.comment_path(5)
```

## Expected Output

```
/posts/1/comments
/comments/5
```
