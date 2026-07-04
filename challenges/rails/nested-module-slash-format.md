---
wiki: rails/routing/scope-vs-namespace
section: Module Path Format
kind: write-code
env: rails
questions:
- Why must nested modules use slash notation instead of Ruby's double colon in routing options?
created: 2026-07-03
---

## Brief

Route /posts to Api::V1::PostsController. The module string must follow the directory structure, not Ruby constant syntax.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  scope module: "TODO" do # TODO: nested module so /posts hits Api::V1::PostsController
    resources :posts, only: :index
  end
end
puts routes.routes.first.defaults[:controller]
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  scope module: "api/v1" do
    resources :posts, only: :index
  end
end
puts routes.routes.first.defaults[:controller]
```

## Expected Output

```
api/v1/posts
```
