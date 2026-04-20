---
title: Shallow Routing
aliases:
- shallow nesting
- shallow routes
- shallow true
tags:
- rails
- routing
category: work
created: '2026-04-13'
updated: '2026-04-13'
source_skill: study-walkthrough
depth: 1
next_review: '2026-04-24'
review_interval: 8
probe_sections:
- The Split
- Why This Split
- Named Helpers Change Too
- Applying to All Nested Resources
last_probed: []
---

# Shallow Routing

Nested resources produce long URLs like `/posts/:post_id/comments/:id`. Once you have the comment's `:id`, the parent prefix is redundant. `shallow: true` flattens the routes that don't need the parent.

## The Split

```ruby
resources :posts do
  resources :comments, shallow: true
end
```

Routes that **need the parent** (no `:id` yet) stay nested:

| HTTP | URL                          | Action |
|------|------------------------------|--------|
| GET  | /posts/:post_id/comments     | index  |
| GET  | /posts/:post_id/comments/new | new    |
| POST | /posts/:post_id/comments     | create |

Routes where **`:id` is enough** become flat:

| HTTP   | URL                | Action  |
|--------|--------------------|---------|
| GET    | /comments/:id      | show    |
| GET    | /comments/:id/edit | edit    |
| PATCH  | /comments/:id      | update  |
| DELETE | /comments/:id      | destroy |

## Why This Split

`index`, `new`, and `create` need the parent because you're asking "which post's comments?" Once a comment exists and has an ID, it's self-identifying -- no need to repeat the parent in the URL.

## Named Helpers Change Too

Nested routes keep the parent prefix, shallow ones drop it:

```ruby
post_comments_path(@post)      # index, new, create
comment_path(@comment)         # show, edit, update, destroy
```

## Applying to All Nested Resources

Wrap the parent in `shallow` to apply to every nested resource:

```ruby
shallow do
  resources :posts do
    resources :comments
    resources :likes
  end
end
```

## Related Concepts

- [[rails/singular-resource]] -- another way to simplify route URLs
- [[rails/scope-vs-namespace]] -- controlling URL structure with scope
