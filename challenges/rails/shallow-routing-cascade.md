---
wiki: rails/routing/shallow-routing
section: Applying to All Nested Resources
kind: write-code
env: rails
questions:
- What are the two equivalent ways to make every nested resource shallow?
- What would happen to the like_path helper if shallow were set only on comments?
created: 2026-07-03
---

## Brief

Two nested resources under posts. Make both shallow by changing only the parent line, so the flat member helpers below resolve.

## Stub

```ruby
Rails.application.routes.draw do
  # TODO: make every nested resource shallow without touching the nested lines
  resources :posts do
    resources :comments
    resources :likes
  end
end

helpers = Rails.application.routes.url_helpers
puts helpers.comment_path(5)
puts helpers.like_path(9)
```

## Solution

```ruby
Rails.application.routes.draw do
  resources :posts, shallow: true do
    resources :comments
    resources :likes
  end
end

helpers = Rails.application.routes.url_helpers
puts helpers.comment_path(5)
puts helpers.like_path(9)
```

## Expected Output

```
/comments/5
/likes/9
```
