---
title: Path Helper Naming
aliases:
- rename path helper
- as option routes
- path helper as
- _index suffix
tags:
- rails
- routing
category: work
created: '2026-04-14'
updated: '2026-04-14'
source_skill: study-walkthrough
depth: 1
next_review: '2026-04-22'
review_interval: 4
probe_sections:
- Renaming with `as:`
- The `_index` Suffix
- 'Fix: Set `as:` Explicitly'
- Verifying
last_probed: []
---

# Path Helper Naming

Rails derives path helper names from resource and action names. The `as:` option overrides the default. A `_index` suffix on a helper is a signal that Rails couldn't disambiguate singular and plural forms.

## Renaming with `as:`

On a custom route:

```ruby
resources :posts do
  collection do
    get :search, as: :find  # find_posts_path
  end
end
```

On the resource itself:

```ruby
resources :posts, as: :articles
# articles_path, article_path(@post), new_article_path, edit_article_path(@post)
```

On a bare route:

```ruby
get :archive, to: 'posts#archive', as: :post_archive  # post_archive_path
```

## The `_index` Suffix

When `bin/rails routes` shows a helper like `foo_index`, it means Rails appended `_index` to disambiguate the collection helper. This happens when the inflector cannot cleanly distinguish the singular and plural forms of the resource name.

Example from a real codebase:

```ruby
resources(
  :inbox_items_read_markers,
  only: %i[create],
  path: 'inboxItemsReadMarker',
  controller: :read_marker
)
```

Helper generated: `api_v2_inbox_items_read_marker_index_path`

Rails sees an inflection ambiguity on `inbox_items_read_markers` and guards against a future collision with a member helper by suffixing the collection helper with `_index`.

## Fix: Set `as:` Explicitly

```ruby
resources(
  :inbox_items_read_markers,
  only: %i[create],
  path: 'inboxItemsReadMarker',
  controller: :read_marker,
  as: :inbox_items_read_markers
)
```

Helper becomes: `api_v2_inbox_items_read_markers_path`.

## Verifying

Always check with:

```bash
bin/rails routes | grep <helper_fragment>
```

Path helpers are the contract between routes and views/controllers -- a rename affects every caller.

## Related Concepts

- [[rails/collection-and-member-routes]] -- where `as:` applies to custom actions
- [[rails/scope-vs-namespace]] -- `as:` on scope/namespace controls prefix on all nested helpers
- [[rails/shallow-routing]] -- shallow mode changes helper names by dropping the parent prefix
