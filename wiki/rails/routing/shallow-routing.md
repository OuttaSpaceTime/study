---
title: Shallow Routing
aliases:
- shallow nesting
- shallow routes
- shallow true
tags:
- rails
- routing
created: '2026-04-13'
updated: '2026-06-01'
source_skill: study-walkthrough
next_review: '2026-07-21'
review_interval: 50
flashcard_ids: []
---

# Shallow Routing

Nested resources produce long URLs like `/posts/:post_id/comments/:id`. Once you have the comment's `:id`, the parent prefix is redundant. `shallow: true` flattens the routes that don't need the parent.

## How shallow routing splits member vs collection routes

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

Equivalently, pass `shallow: true` as an option on the parent -- it cascades to every nested resource inside the block:

```ruby
resources :posts, shallow: true do
  resources :comments
  resources :likes
end
```

Both forms generate identical routes. Per the Rails guide, you can specify the `:shallow` option on the parent resource, in which case all of its nested resources will be shallow.

## Related Concepts

- [[rails/routing/singular-resource]] -- another way to simplify route URLs
- [[rails/routing/scope-vs-namespace]] -- controlling URL structure with scope
