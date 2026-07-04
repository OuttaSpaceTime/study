---
wiki: rails/routing/routing-concerns
section: Extract a Concern
kind: write-code
env: rails
questions:
- What does the concerns option expand to when Rails draws the routes?
- Are routes generated through a concern any different from writing the nested resources inline?
created: 2026-07-03
---

## Brief

A :social concern is already defined, but neither resource uses it yet. Apply it to both so each gets the nested comments route.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  concern :social do
    resources :comments, only: :index
  end
  resources :posts # TODO: include the :social concern on posts and articles
  resources :articles
end
puts routes.routes.map { |r| r.path.spec.to_s }.grep(/comments/)
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  concern :social do
    resources :comments, only: :index
  end
  resources :posts, concerns: :social
  resources :articles, concerns: :social
end
puts routes.routes.map { |r| r.path.spec.to_s }.grep(/comments/)
```

## Expected Output

```
/posts/:post_id/comments(.:format)
/articles/:article_id/comments(.:format)
```
