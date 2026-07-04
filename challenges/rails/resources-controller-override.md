---
wiki: rails/routing/scope-vs-namespace
section: "The controller: Option"
kind: predict-output
env: rails
questions:
- "How does the controller: option differ from module: in what it changes on a route?"
- "Why does namespace not accept the controller: option?"
created: 2026-07-03
---

## Brief

A resource whose controller is overridden. Predict which of the three knobs actually change.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :photos, only: :index, controller: "images"
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
  resources :photos, only: :index, controller: "images"
end
r = routes.routes.first
puts "URL:        #{r.path.spec}"
puts "Controller: #{r.defaults[:controller]}"
puts "Helper:     #{r.name}_path"
```

## Expected Output

```
URL:        /photos(.:format)
Controller: images
Helper:     photos_path
```
