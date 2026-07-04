---
wiki: rails/routing/path-helper-naming
section: Renaming with `as:`
kind: write-code
env: rails
questions:
- What does as: change on a route, and what does it leave untouched?
- Where else besides a custom collection route can you put as:?
created: 2026-07-03
---

## Brief

A custom collection action gets the default helper name search_posts_path. Rename the helper so callers use find_posts_path while the URL stays /posts/search.

## Stub

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts do
    collection do
      get :search # TODO: rename the helper so find_posts_path works
    end
  end
end

puts routes.url_helpers.find_posts_path
```

## Solution

```ruby
routes = ActionDispatch::Routing::RouteSet.new
routes.draw do
  resources :posts do
    collection do
      get :search, as: :find
    end
  end
end

puts routes.url_helpers.find_posts_path
```

## Expected Output

```
/posts/search
```
