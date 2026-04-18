---
title: Singular Resource
aliases:
- resource singular
- resource vs resources
- singular route
tags:
- rails
- routing
created: '2026-04-13'
updated: '2026-04-16'
source_skill: study-walkthrough
depth: 1
next_review: '2026-04-24'
review_interval: 8
probe_sections:
- 6 Routes, Not 7
- Controller Is Still Plural
- When to Use
- How Identity Is Resolved
- Nesting Works the Same
last_probed: []
---

# Singular Resource

`resource` (singular) generates routes for a resource where there is only ever one instance scoped to the current context -- no `:id` parameter, no `index` action.

## 6 Routes, Not 7

```ruby
resource :profile
```

Generates:

| HTTP   | URL             | Action  |
|--------|-----------------|---------|
| GET    | /profile/new    | new     |
| POST   | /profile        | create  |
| GET    | /profile        | show    |
| GET    | /profile/edit   | edit    |
| PATCH  | /profile        | update  |
| DELETE | /profile        | destroy |

No `index` -- there's only one. No `:id` in any URL -- identity comes from context (e.g., the session).

## Controller Is Still Plural

`resource :profile` routes to `ProfilesController`, not `ProfileController`. Rails convention: controllers are always plural regardless of route singularity.

## When to Use

Use `resource` when the current user (or current context) implies which record:

- `resource :profile` -- user's own profile
- `resource :cart` -- user's shopping cart
- `resource :dashboard` -- user's dashboard
- `resource :session` -- authentication session

If you need `/profiles/42` to view different users' profiles, use `resources` instead.

## How Identity Is Resolved

There's no `:id` in the URL, so the controller resolves identity from the **server-side session** -- typically `current_user`:

```ruby
class ProfilesController < ApplicationController
  def show
    @profile = current_user.profile
  end
end
```

No extra parameters in the request. The authenticated session already knows *who* is asking, so the URL doesn't need to say *which* record.

## Nesting Works the Same

```ruby
resource :profile do
  resources :addresses
end
# GET /profile/addresses => addresses#index
# GET /profile/addresses/:id => addresses#show
```

## Related Concepts

- [[rails/scope-vs-namespace]] -- controlling URL prefix, module, and helper names
- [[rails/shallow-routing]] -- flattening nested resource URLs
