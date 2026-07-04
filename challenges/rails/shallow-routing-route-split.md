---
wiki: rails/routing/shallow-routing
section: How shallow routing splits member vs collection routes
kind: predict-output
env: rails
questions:
- Which actions stay nested under the parent, and what do they have in common?
- Why does destroy not need the post id in its URL?
created: 2026-07-03
---

## Brief

One nested resource with shallow enabled, then a dump of every comments route. Predict which URLs keep the /posts/:post_id prefix and which are flat.

## Stub

```ruby
Rails.application.routes.draw do
  resources :posts do
    resources :comments, shallow: true
  end
end

Rails.application.routes.routes.each do |r|
  next unless r.defaults[:controller] == "comments"
  path = r.path.spec.to_s.sub("(.:format)", "")
  puts format("%-7s %-29s %s", r.verb, path, r.defaults[:action])
end
```

## Solution

```ruby
Rails.application.routes.draw do
  resources :posts do
    resources :comments, shallow: true
  end
end

Rails.application.routes.routes.each do |r|
  next unless r.defaults[:controller] == "comments"
  path = r.path.spec.to_s.sub("(.:format)", "")
  puts format("%-7s %-29s %s", r.verb, path, r.defaults[:action])
end
```

## Expected Output

```
GET     /posts/:post_id/comments      index
POST    /posts/:post_id/comments      create
GET     /posts/:post_id/comments/new  new
GET     /comments/:id/edit            edit
GET     /comments/:id                 show
PATCH   /comments/:id                 update
PUT     /comments/:id                 update
DELETE  /comments/:id                 destroy
```
