---
title: Routing Concerns
aliases:
- rails concern
- route concerns
- routing concern
tags:
- rails
- routing
created: '2026-04-13'
updated: '2026-04-13'
source_skill: study-walkthrough
depth: 1
next_review: '2026-06-16'
review_interval: 48
probe_sections:
- 'The problem: duplicated route blocks across resources'
- Extract a Concern
- Multiple Concerns
- When to extract a routing concern
last_probed:
- When to extract a routing concern
- 'The problem: duplicated route blocks across resources'
- Extract a Concern
- Multiple Concerns
flashcard_ids: []
---

# Routing Concerns

A concern extracts a reusable block of route definitions. It's purely DRY -- the generated routes are identical to writing them inline.

## The problem: duplicated route blocks across resources

Multiple resources sharing the same nested structure:

```ruby
# bad -- repetition
resources :posts do
  resources :comments
  resources :likes
end

resources :articles do
  resources :comments
  resources :likes
end

resources :videos do
  resources :comments
  resources :likes
end
```

## Extract a Concern

```ruby
# good
concern :social do
  resources :comments
  resources :likes
end

resources :posts, concerns: :social
resources :articles, concerns: :social
resources :videos, concerns: :social
```

Same routes, same helpers, same controller mapping. The concern is just a named chunk of routing code.

## Multiple Concerns

A resource can include multiple concerns:

```ruby
concern :social do
  resources :comments
  resources :likes
end

concern :taggable do
  resources :tags, only: [:index, :create, :destroy]
end

resources :posts, concerns: [:social, :taggable]
resources :articles, concerns: [:social]
```

## When to extract a routing concern

Worth it when 3+ resources share the same nested structure. For just 2, the duplication is tolerable and easier to read.

## Related Concepts

- [[rails/routing/scope-vs-namespace]] -- another route organization tool
- [[rails/routing/route-organization]] -- splitting routes into files with `draw`
