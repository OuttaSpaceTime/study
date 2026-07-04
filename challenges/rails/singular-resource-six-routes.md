---
wiki: rails/routing/singular-resource
section: "6 Routes, Not 7"
kind: predict-output
env: rails
questions:
- Which of the seven resources actions is missing here, and why would it make no sense?
- Why does no generated path contain an :id segment?
created: 2026-07-03
---

## Brief

A fresh route set draws `resource :profile`. Predict every line the loop prints: verb, path, and action.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw { resource :profile }
routes.routes.each do |r|
  puts "#{r.verb.ljust(7)} #{r.path.spec.to_s.sub('(.:format)', '')}  => #{r.defaults[:action]}"
end
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw { resource :profile }
routes.routes.each do |r|
  puts "#{r.verb.ljust(7)} #{r.path.spec.to_s.sub('(.:format)', '')}  => #{r.defaults[:action]}"
end
```

## Expected Output

```
GET     /profile/new  => new
GET     /profile/edit  => edit
GET     /profile  => show
PATCH   /profile  => update
PUT     /profile  => update
DELETE  /profile  => destroy
POST    /profile  => create
```
