---
wiki: rails/routing/scope-vs-namespace
section: The Three Knobs
kind: predict-output
env: rails
questions:
- Which three things does namespace :admin set at once, and what is each one's effect for resources :posts?
- Which scope option replaces each of the three knobs individually?
created: 2026-07-03
---

## Brief

A single namespace block around one resource. Predict the URL, the controller default, and the helper name that come out.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  namespace :admin do
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
  namespace :admin do
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
URL:        /admin/posts(.:format)
Controller: admin/posts
Helper:     admin_posts_path
```
