---
wiki: rails/routing/route-organization
section: defaults -- Set Shared Parameters
kind: predict-output
env: rails
questions:
- The URL /posts contains no .json suffix, so where does the format parameter come from?
- What happens to params[:format] when a client requests /posts.xml despite the defaults block?
created: 2026-07-03
---

## Brief

Posts are drawn inside a `defaults format: :json` block, comments are not. Predict the params each URL recognizes to, keeping in mind neither URL mentions a format.

## Stub

```ruby
class PostsController < ActionController::Base; end
class CommentsController < ActionController::Base; end

Rails.application.routes.draw do
  defaults format: :json do
    resources :posts, only: [:index]
  end
  resources :comments, only: [:index]
end

puts Rails.application.routes.recognize_path("/posts").inspect
puts Rails.application.routes.recognize_path("/comments").inspect
```

## Solution

```ruby
class PostsController < ActionController::Base; end
class CommentsController < ActionController::Base; end

Rails.application.routes.draw do
  defaults format: :json do
    resources :posts, only: [:index]
  end
  resources :comments, only: [:index]
end

puts Rails.application.routes.recognize_path("/posts").inspect
puts Rails.application.routes.recognize_path("/comments").inspect
```

## Expected Output

```
{:format=>:json, :controller=>"posts", :action=>"index"}
{:controller=>"comments", :action=>"index"}
```
