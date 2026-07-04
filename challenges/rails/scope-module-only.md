---
wiki: rails/routing/scope-vs-namespace
section: Scope Picks and Chooses
kind: write-code
env: rails
questions:
- Which scope option changes only the controller module while leaving URL and helper untouched?
- "What real-world refactoring does scope module: :admin enable without breaking existing URLs?"
created: 2026-07-03
---

## Brief

Route GET /posts to Admin::PostsController while keeping the plain posts_path helper. Pick exactly one of the three knobs.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  scope do # TODO: keep URL and helper as-is, but route to Admin::PostsController
    resources :posts, only: :index
  end
end
r = routes.routes.first
puts "URL:        #{r.path.spec}"
puts "Controller: #{r.defaults[:controller]}"
puts "Helper:     #{r.name}_path"
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  scope module: :admin do
    resources :posts, only: :index
  end
end
r = routes.routes.first
puts "URL:        #{r.path.spec}"
puts "Controller: #{r.defaults[:controller]}"
puts "Helper:     #{r.name}_path"
```

## Expected Output

```
URL:        /posts(.:format)
Controller: admin/posts
Helper:     posts_path
```
