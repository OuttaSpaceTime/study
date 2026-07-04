---
wiki: rails/routing/path-helper-naming
section: The `_index` Suffix
kind: predict-output
env: rails
questions:
- Why does one collection helper get an _index suffix while the other does not?
- What future collision is Rails guarding against with the suffix?
created: 2026-07-03
---

## Brief

Two index-only resources, one countable and one uncountable. Predict the named helper each collection route gets.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: :index
  resources :news, only: :index
end

routes.routes.each do |r|
  puts format("%-10s %s", r.name, r.path.spec.to_s.sub("(.:format)", ""))
end
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: :index
  resources :news, only: :index
end

routes.routes.each do |r|
  puts format("%-10s %s", r.name, r.path.spec.to_s.sub("(.:format)", ""))
end
```

## Expected Output

```
posts      /posts
news_index /news
```
