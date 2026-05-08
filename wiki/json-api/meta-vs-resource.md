---
title: meta vs resource
aliases:
- JSON:API meta
- when to use meta vs resource
- identity test for API design
tags:
- api-design
- json-api
- rest
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- The identity test
- meta is safe to ignore
- Anti-patterns that should be resources
- Authorization is not a serialisation concern
last_probed:
- The identity test
- meta is safe to ignore
- Anti-patterns that should be resources
- Authorization is not a serialisation concern
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# meta vs resource

The decision "should this go in `meta`, on the resource as an attribute, or be its own resource?" comes up daily when designing an API. JSON:API gives you a heuristic that decides it cleanly. The **identity test**.

## TL;DR

- If the data has identity → **resource**. If it is a property of the response itself → **`meta`**. If it is a tightly-coupled scalar value of a resource → **attribute**.
- `meta` should be safe to ignore. The moment business logic depends on it, it should have been an attribute or a resource.
- Authorization controls visibility, not sparse fieldsets. `fields[]` is a client preference, not a security boundary.

## The identity test

Ask whether the data has identity. It does when any of these hold:

- You would want to fetch it independently
- You would want to link to it from somewhere else
- You would want to update or version it
- It outlives the request that returned it

If yes → resource. If no → `meta` (for response-scoped info) or attribute (for scalar values tied to an existing resource).

Concrete examples:

| Data                                | Identity? | Where it goes                                    |
| ----------------------------------- | --------- | ------------------------------------------------ |
| `total_count` of a paginated query  | No        | `meta`: describes the query result              |
| `request_id` for tracing            | No        | `meta` (or HTTP header)                          |
| Last invoice timestamp on an org    | No        | Attribute on `organizations`                     |
| User's unread notification count    | No        | Attribute on `users` (or `notifications-summary` if structured) |
| Activity log (paginated, filterable)| Yes       | Resource at `/activities` or `/orgs/X/activities`|
| Average article rating              | Borderline | Resource `article-stats` if cacheable, else attribute |
| User settings                       | Yes       | Resource `settings` linked from user             |

## meta is safe to ignore

`meta` is for **properties of the response itself**, not properties of a resource:

```json
{
  "data": [...],
  "meta": {
    "total_count": 1543,
    "request_id": "abc-123",
    "deprecation": "v1 sunsets 2027-01"
  }
}
```

The litmus test for `meta` correctness. A generic client that ignores `meta` entirely (caches, logging, dev tools, deserialisers) MUST still function correctly. If a UI breaks when `meta` is dropped, the data was misclassified. Promote it.

## Anti-patterns that should be resources

These all want to be resources, not stuffed into `meta`:

- **Aggregates users care about** (e.g. average article rating, view count, like count). Promote to `article-stats` resource. You then get caching, sparse fieldsets, includes, and a stable URL.
- **Settings or preferences.** `users.relationships.settings` → `settings` resource. Not `meta.settings`.
- **Anything you would want to filter or sort by.** Only attributes (and sometimes relationship traversal) participate in `filter[]` and `sort`. Hiding values in `meta` puts them out of reach of the reserved query families.
- **Per-request stats injected into every response** (e.g. quota, rate limits). These belong in HTTP headers (`X-RateLimit-Remaining`) or a dedicated `/usage` endpoint. Stuffing them into every response inflates payloads, pollutes caches with user-specific data, and couples every endpoint to the quota subsystem.

## Authorization is not a serialisation concern

Consider this temptation. "This attribute should only be visible to admins, so I will use sparse fieldsets to hide it." Wrong layer.

- Authorization runs first, before serialisation. Server omits the attribute (or returns `403`) for unauthorised callers.
- Sparse fieldsets are a *client preference* about which attributes to include. A non-admin client sending `fields[organizations]=member_limit` would still see the field if your only protection were sparse fieldsets. They are not a security boundary.

The corollary. When you decide "limit is admin-only and lives on the org," the design is "attribute on `organizations` + authz omits it for non-admins." Not "attribute that we hide via `fields[]`."

## Related Concepts

- [[json-api/json-api-index]]: graph-protocol mental model
- [[json-api/document-structure]]: resource, attribute, relationship terminology
- [[json-api/query-conventions]]: sparse fieldsets, filter, sort

## References

- [JSON:API v1.1 spec, Meta Information](https://jsonapi.org/format/#document-meta): official rules for `meta`
- [JSON:API v1.1 spec, Resource Objects](https://jsonapi.org/format/#document-resource-objects): what counts as a resource
