---
title: Scope vs Namespace
aliases:
- rails scope
- rails namespace
- scope vs namespace routing
- route scope
tags:
- rails
- routing
created: '2026-04-13'
updated: '2026-04-16'
source_skill: study-walkthrough
flashcard_ids: []
---

# Scope vs Namespace

`namespace` sets three things at once. `scope` lets you pick which ones you want.

## The Three Knobs

`namespace :admin` applies all three:

| Knob             | Effect                                     | Scope option   |
|------------------|--------------------------------------------|----------------|
| URL prefix       | `/admin/posts`                             | `scope :admin` |
| Controller module| `Admin::PostsController` in `admin/` dir   | `module:`      |
| Helper prefix    | `admin_posts_path`                         | `as:`          |

```ruby
# namespace sets all three
namespace :admin do
  resources :posts
end
# /admin/posts => Admin::PostsController, admin_posts_path
```

## Scope Picks and Chooses

```ruby
# URL prefix only
scope :admin do
  resources :posts
end
# /admin/posts => PostsController, posts_path

# Module only (no URL change)
scope module: :admin do
  resources :posts
end
# /posts => Admin::PostsController, posts_path

# Helper prefix only
scope as: :admin do
  resources :posts
end
# /posts => PostsController, admin_posts_path
```

## Module Path Format

Use slash-separated paths for nested modules, not Ruby's `::`:

```ruby
# good
scope module: "api/v1" do
  resources :posts
end
# /posts => Api::V1::PostsController

# bad -- won't resolve the directory structure
scope module: "api::v1" do
  resources :posts
end
```

## Per-Resource Options

`resources` accepts the same options directly:

```ruby
resources :posts, module: :admin       # module only
resources :posts, path: :articles      # changes URL segment
resources :posts, as: :blog_posts      # changes helper name
```

## The Controller: Option

`controller:` pins all routes to a specific controller, unlike `module:` which sets the namespace. It is supported by:

- **`scope`** -- wraps multiple routes under one controller
- **`resources` / `resource`** -- overrides the controller inferred from the resource name
- **`get` / `post` / `put` / `delete` / `patch` / `match`** -- explicit controller for non-resourceful routes

`namespace` does **not** accept `controller:` -- it sets the module automatically.

```ruby
# scope: pin loose pages to one controller
scope controller: :pages do
  get "about"    # => pages#about
  get "contact"  # => pages#contact
end

# shorthand: `controller` block == `scope controller:`
controller :pages do
  get "about"    # => pages#about
  get "contact"  # => pages#contact
end

# resources: override inferred controller
resources :photos, controller: "images"
# => ImagesController, not PhotosController

# non-resourceful: explicit controller
get "/users/:id", controller: "users", action: :show
```

Use directory notation for namespaced controllers (`"admin/posts"` not `"Admin::Posts"`).

## When to Use scope vs namespace vs module

- **`namespace`**: you want all three knobs (typical for admin panels, API versions)
- **`scope`**: you want to change one knob without the others
- **`scope` wrapping multiple resources**: apply options to several resources at once, avoiding repetition on each `resources` call

Common real-world case for `scope module:`. Refactoring `PostsController` into `Admin::PostsController` without breaking existing URLs.

## Related Concepts

- [[rails/routing/singular-resource]] -- `resource` for single-instance routes
- [[rails/routing/routing-concerns]] -- extracting reusable route patterns
