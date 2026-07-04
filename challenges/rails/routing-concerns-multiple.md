---
wiki: rails/routing/routing-concerns
section: Multiple Concerns
kind: predict-output
env: rails
questions:
- How do you attach more than one concern to a single resource?
- Which nested routes does articles get here, and why is there no tags route under it?
created: 2026-07-03
---

## Brief

Posts includes two concerns, articles only one. Predict which nested paths exist.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  concern :social do
    resources :comments, only: :index
  end
  concern :taggable do
    resources :tags, only: :index
  end
  resources :posts, concerns: [:social, :taggable]
  resources :articles, concerns: [:social]
end
puts routes.routes.map { |r| r.path.spec.to_s }.grep(/comments|tags/)
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  concern :social do
    resources :comments, only: :index
  end
  concern :taggable do
    resources :tags, only: :index
  end
  resources :posts, concerns: [:social, :taggable]
  resources :articles, concerns: [:social]
end
puts routes.routes.map { |r| r.path.spec.to_s }.grep(/comments|tags/)
```

## Expected Output

```
/posts/:post_id/comments(.:format)
/posts/:post_id/tags(.:format)
/articles/:article_id/comments(.:format)
```
