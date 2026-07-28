---
title: Collection and Member Routes
aliases:
- collection route
- member route
- collection vs member
- custom resource routes
tags:
- rails
- routing
created: '2026-04-14'
updated: '2026-04-14'
source_skill: study-walkthrough
next_review: '2026-07-07'
review_interval: 30
flashcard_ids: []
---

# Collection and Member Routes

`resources` gives you 7 RESTful routes. When you need custom endpoints on the same controller, `collection` and `member` add them without creating a new resource.

## The Decision Table

| Tool | Acts on | Has `:id`? | Example URL |
|------|---------|------------|-------------|
| `member` | One record | Yes | `/posts/:id/archive` |
| `collection` | All records | No | `/posts/search` |
| nested `resources` | Sub-resource | Parent + child IDs | `/posts/:post_id/comments/:id` |

Rule of thumb. If the URL doesn't need a specific record's ID, it's a collection route.

## Declaring collection and member routes

```ruby
resources :posts do
  member do
    post :archive      # POST /posts/:id/archive => posts#archive
  end

  collection do
    get :search        # GET /posts/search => posts#search
    delete :bulk_destroy  # DELETE /posts/bulk_destroy => posts#bulk_destroy
  end
end
```

Single-line form with `on:`:

```ruby
resources :posts do
  post :archive, on: :member
  get :search, on: :collection
end
```

## Routing to a Different Controller

The `to:` option overrides the controller and action. It changes only the dispatch target -- the URL pattern and param names stay the same.

```ruby
resources :posts do
  member do
    post :flag, to: 'moderation#flag'
    # POST /posts/:id/flag => ModerationController#flag
    # params[:id] is the post -- still :id, not :post_id
  end
end
```

`to:` is an absolute controller reference. It does not namespace the controller under the resource -- `'moderation#flag'` always means `ModerationController`, not `Posts::ModerationController`.

## Param Naming Rules

- **member route**: the resource's own ID is always `params[:id]`, even with `to:` pointing elsewhere
- **nested resource**: parent becomes `params[:post_id]`, child is `params[:id]`
- **collection route**: no `:id` in the URL at all

```ruby
resources :posts do
  resources :comments do
    member do
      post :flag, to: 'moderation#flag'
      # POST /posts/:post_id/comments/:id/flag
      # params[:post_id] = the post, params[:id] = the comment
    end
  end
end
```

## When to use collection vs member

- **One-off action on a single record** (archive, publish, flag) -> `member`
- **Action across the collection** (search, export CSV, bulk delete) -> `collection`
- **Whole new CRUD lifecycle** (comments, tags, attachments) -> nested `resources`

## Related Concepts

- [[rails/routing/path-helper-naming]] -- renaming generated helpers with `as:`, and the `_index` suffix
- [[rails/routing/shallow-routing]] -- flattens nested resource URLs once the child ID is known
- [[rails/routing/singular-resource]] -- `resource` (singular) for resources without IDs
- [[rails/routing/scope-vs-namespace]] -- controlling URL prefix and controller module
- [[rails/routing/routing-concerns]] -- extracting shared route patterns into reusable blocks
