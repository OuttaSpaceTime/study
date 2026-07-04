---
wiki: rails/routing/singular-resource
section: Nesting Works the Same
kind: write-code
env: rails
questions:
- Why does the nested child keep its :id segment while the parent path has none?
- Why does the nested addresses collection get an index action when the singular parent does not?
created: 2026-07-03
---

## Brief

Declare routes so that a user's addresses live under an id-less profile path. Both lookups below must resolve.

## Stub

```ruby
class AddressesController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  # TODO: nest addresses under a singular profile resource
end

puts routes.recognize_path("/profile/addresses", method: :get)
puts routes.recognize_path("/profile/addresses/7", method: :get)
```

## Solution

```ruby
class AddressesController < ActionController::Base; end

routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resource :profile do
    resources :addresses
  end
end

puts routes.recognize_path("/profile/addresses", method: :get)
puts routes.recognize_path("/profile/addresses/7", method: :get)
```

## Expected Output

```
{:controller=>"addresses", :action=>"index"}
{:controller=>"addresses", :action=>"show", :id=>"7"}
```
