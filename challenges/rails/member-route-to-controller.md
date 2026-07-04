---
wiki: rails/routing/collection-and-member-routes
section: Routing to a Different Controller
kind: predict-output
env: rails
questions:
- What does the to: option change, and what does it leave untouched?
- Why does 'moderation#flag' resolve to ModerationController rather than Posts::ModerationController?
created: 2026-07-03
---

## Brief

A member route with to: pointing at another controller. Predict the generated path, the recognized controller, and the name of the id param.

## Stub

```ruby
class ModerationController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    post :flag, to: "moderation#flag", on: :member
  end
end

puts routes.url_helpers.flag_post_path(5)
p routes.recognize_path("/posts/5/flag", method: :post)
```

## Solution

```ruby
class ModerationController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts, only: [] do
    post :flag, to: "moderation#flag", on: :member
  end
end

puts routes.url_helpers.flag_post_path(5)
p routes.recognize_path("/posts/5/flag", method: :post)
```

## Expected Output

```
/posts/5/flag
{:controller=>"moderation", :action=>"flag", :id=>"5"}
```
