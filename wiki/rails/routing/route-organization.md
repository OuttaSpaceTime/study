---
title: Route Organization
aliases:
- rails draw
- route files
- routes draw
- rails defaults
tags:
- rails
- routing
created: '2026-04-13'
updated: '2026-04-13'
source_skill: study-walkthrough
next_review: '2026-07-18'
review_interval: 1
flashcard_ids: []
---

# Route Organization

Two tools keep `config/routes.rb` manageable as it grows. `draw` splits routes into files and `defaults` sets shared parameters.

## draw -- Split Routes into Files

```ruby
# config/routes.rb
Rails.application.routes.draw do
  draw :admin
  draw :api

  resources :posts
end
```

```ruby
# config/routes/admin.rb
namespace :admin do
  resources :users
  resources :settings
end
```

```ruby
# config/routes/api.rb
namespace :api do
  namespace :v1 do
    resources :posts
  end
end
```

`draw :admin` loads `config/routes/admin.rb` and evaluates it in the same routing context. The routes behave exactly as if they were inline -- it's purely file organization.

Use `draw` when `routes.rb` gets long enough that navigating it becomes painful. Group by domain area (admin, API, public).

## defaults -- Set Shared Parameters

`defaults` sets parameters on routes without them appearing in the URL:

```ruby
defaults format: :json do
  resources :posts
  resources :comments
end
```

Every route inside has `params[:format]` set to `"json"` unless the request explicitly overrides it. Useful for API-only sections where you don't want `.json` in every URL.

Also works per-resource:

```ruby
resources :posts, defaults: { format: :json }
```

## Related Concepts

- [[rails/routing/scope-vs-namespace]] -- `namespace` and `scope` for URL/module/helper prefixing
- [[rails/routing/routing-concerns]] -- DRY route extraction within a single file
