---
wiki: rails/routing/collection-and-member-routes
section: Param Naming Rules
kind: predict-output
env: rails
questions:
- Which record is params[:id] here, and what rule decides which resource gets the _id-prefixed param?
- What would the URL and params look like if flag were a collection route on comments instead?
created: 2026-07-03
---

## Brief

A member route on a nested resource. Predict the exact param names Rails extracts from the URL.

## Stub

```ruby
class CommentsController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    resources :comments, only: [] do
      post :flag, on: :member
    end
  end
end

p routes.recognize_path("/posts/7/comments/3/flag", method: :post)
```

## Solution

```ruby
class CommentsController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    resources :comments, only: [] do
      post :flag, on: :member
    end
  end
end

p routes.recognize_path("/posts/7/comments/3/flag", method: :post)
```

## Expected Output

```
{:controller=>"comments", :action=>"flag", :post_id=>"7", :id=>"3"}
```
