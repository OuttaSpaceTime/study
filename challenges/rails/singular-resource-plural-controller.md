---
wiki: rails/routing/singular-resource
section: Controller Is Still Plural
kind: write-code
env: rails
questions:
- Why does the singular route dispatch to a plural controller?
- What error does recognize_path raise if you only define ProfileController?
created: 2026-07-03
---

## Brief

`recognize_path` constantizes the controller a route points to and raises if the class is missing. Define the one class that makes the lookup succeed.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw { resource :profile }

class TODOController < ActionController::Base; end # TODO: name the class this route dispatches to

puts routes.recognize_path("/profile", method: :get)
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw { resource :profile }

class ProfilesController < ActionController::Base; end

puts routes.recognize_path("/profile", method: :get)
```

## Expected Output

```
{:controller=>"profiles", :action=>"show"}
```
