---
wiki: rails/routing/path-helper-naming
section: "Fix: Set `as:` Explicitly"
kind: write-code
env: rails
questions:
- Why would as: news fail to remove the _index suffix here?
- Does setting as: change the URL that the route matches?
created: 2026-07-03
---

## Brief

The uncountable resource news produces the helper news_index_path. Set as: so the collection helper becomes news_items_path while the URL stays /news.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :news, only: :index # TODO: name the helper news_items_path instead of news_index_path
end

puts routes.url_helpers.news_items_path
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :news, only: :index, as: :news_items
end

puts routes.url_helpers.news_items_path
```

## Expected Output

```
/news
```
