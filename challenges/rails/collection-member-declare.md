---
wiki: rails/routing/collection-and-member-routes
section: Declaring collection and member routes
kind: write-code
env: rails
questions:
- Why does the archive route carry :id in its path while the search route does not?
- What is the block-form equivalent of the single-line on: option?
created: 2026-07-03
---

## Brief

A resource with one member route already declared. Add the collection route using the single-line form, then compare the two generated path patterns.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    post :archive, on: :member
    # TODO: declare a GET search route on the collection, single-line form
  end
end
routes.routes.each { |r| puts "#{r.verb} #{r.path.spec}" }
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    post :archive, on: :member
    get :search, on: :collection
  end
end
routes.routes.each { |r| puts "#{r.verb} #{r.path.spec}" }
```

## Expected Output

```
POST /posts/:id/archive(.:format)
GET /posts/search(.:format)
```
