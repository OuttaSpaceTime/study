---
title: Query conventions
aliases:
- JSON:API sparse fieldsets
- JSON:API pagination
- JSON:API filter
- JSON:API sort
- fields[type]
tags:
- api-design
- json-api
- rest
- pagination
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- The envelope-vs-strategy split
- Sparse fieldsets are per-type, not per-path
- Pagination URLs are opaque to the client
- Cursor vs offset under concurrent inserts
- Sort is precise, filter is deliberately undefined
- Custom query parameters need a non-alpha character
last_probed:
- The envelope-vs-strategy split
- Sparse fieldsets are per-type, not per-path
- Pagination URLs are opaque to the client
- Cursor vs offset under concurrent inserts
- Sort is precise, filter is deliberately undefined
- Custom query parameters need a non-alpha character
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# JSON:API query conventions

There are four reserved query-parameter families (`fields`, `include`, `page`, `filter`, `sort`). The spec is opinionated about the *envelope* (the shape of responses and the family-membership rules) and deliberately *unopinionated* about the *strategy* inside each family. Internalising that split is what lets you reason about every query-parameter decision.

## TL;DR

- The spec mandates the response shape and the reserved query-parameter families. The *strategies* inside `page[*]` and `filter[*]` are server-chosen.
- `fields[TYPE]=a,b` is **per type, not per path**. It applies wherever that type appears in the document.
- Clients walk pagination via `links.next` until it is `null`. Treat the URL as opaque. The server can switch strategies without breaking clients.
- Sort grammar is precise (`sort=-created,title`); filter grammar is reserved-but-undefined. Pick one and document it.
- Custom query parameters MUST contain a non-`a-z` character (e.g. a `[`) to avoid colliding with future reserved names.

## The envelope-vs-strategy split

The recurring meta-rule across `page`, `filter`, and `sort`:

| Aspect              | Spec mandates                                      | Server chooses                                    |
| ------------------- | -------------------------------------------------- | ------------------------------------------------- |
| Pagination          | `links.first/prev/next/last` envelope              | Strategy: offset, cursor, page-number             |
| Filter              | The `filter[*]` family namespace                   | Syntax: `filter[x]=v`, `filter[x][eq]=v`, etc.    |
| Sort                | `?sort=-field,other`, comma-separated, `-` = desc  | Which fields are sortable                         |
| Sparse fieldsets    | `fields[TYPE]=a,b` syntax; behaviour is global     | Which attributes exist per type                   |

The split exists because uniform response envelopes buy you generic tooling (caching layers, deserialisers, dev tools) while uniform strategies cause more pain than they solve (cursor and offset have different correctness/perf trade-offs; one filter syntax cannot fit every query language).

**One heuristic to remember:** the response shape is the contract; the URL grammar inside reserved families is yours.

## Sparse fieldsets are per-type, not per-path

```
GET /articles?include=comments.author&fields[people]=name&fields[comments]=body
```

`fields[TYPE]` selects which attributes to return for *that type, wherever it appears in the document*, including inside `included`. There is no `fields[comments.author]` form; the spec deliberately keeps this per-type, not per-path.

The trap. In one document, you cannot say "give me the article's author with full attributes but the comment authors with only name." Both are `people`, and `fields[people]` applies to all of them.

This is **intentional non-flexibility**. JSON:API is not GraphQL. When you need per-edge field selection, you have outgrown the spec's intent. Promote to a different protocol or accept the trade-off.

> [Note] Authorization is not sparse fieldsets. `fields[]` is a *client preference*, not a *security boundary*. If a field must be hidden from non-admins, server-side authz must omit it before serialisation; do not rely on the client requesting it away.

## Pagination URLs are opaque to the client

The spec mandates the envelope:

- Top-level `links` SHOULD include `first`, `prev`, `next`, `last`. Any may be `null` if not applicable.
- Top-level `meta` is the conventional place for `total_count` if exposed.

The strategy is server-chosen. All three of these are spec-compliant:

```
?page[number]=2&page[size]=20         # page-number — most common
?page[offset]=40&page[limit]=20       # offset
?page[after]=cursor_xyz&page[size]=20 # cursor
```

**Clients should treat pagination URLs as opaque**. Fetch `links.next` until it is `null`. If clients construct `?page[number]=N+1` themselves, the server has lost the ability to change strategy without breaking them.

For cursor pagination, `links.last: null` is normal, because computing the last cursor requires a full count, which defeats the point of cursors. `prev` and `next` are the load-bearing keys.

## Cursor vs offset under concurrent inserts

Why the strategy choice matters:

- **Offset** says "skip the first N rows." If 3 new rows are inserted at the top of the result set while a client paginates, page 2 will re-show 3 items from page 1 (or skip 3, depending on sort direction). The window shifts under the client's feet.
- **Cursor** says "everything after this specific row id / timestamp." Insertions are irrelevant; the window is anchored to a specific row.

Cursor wins for high-churn collections (feeds, comments, logs). Offset is acceptable for slowly-changing data and admin tables. The spec stays out of this choice because the right answer depends on the resource.

## Sort is precise, filter is deliberately undefined

**Sort grammar is exact:**

```
GET /articles?sort=-created,title
```

- Comma-separated, multi-field
- Minus prefix = descending; default ascending
- Server picks which attributes are sortable. Sorting on a non-indexed field is a denial-of-service handout.
- Unknown field SHOULD return `400`.

**Filter grammar is reserved but undefined.** All of these are spec-compliant:

```
?filter[name]=alice               # JSONAPI-Resources style
?filter[name][eq]=alice           # operator style
?filter[name][ne]=alice
?filter[created_at][gt]=2026-01-01
?filter[search]=foo bar           # full-text style
```

Three practical rules:

1. **Pick one filter style and document it.** If you mix `filter[x]=y` and `filter[x][eq]=y` across endpoints, every client has to special-case each one.
2. **Whitelist filterable attributes.** Same DoS reasoning as sort. Forces you to think about which queries you want to support before clients depend on them.
3. **Audit relationship-traversing filters.** `filter[author.name]=Dan` (dot paths through relationships) is convenient, but it commits you to a JOIN you must maintain and can N+1 silently.

## Custom query parameters need a non-alpha character

Per v1.1, any query parameter your server defines outside the reserved families MUST contain at least one non-`a-z` character. This is to avoid colliding with future reserved family names.

```
?tags_any=X,Y,Z   # OK, contains underscore
?tagsAny=X,Y,Z    # OK, contains an uppercase letter
?tags=X,Y,Z       # NOT compliant, could collide with a future reserved family
?filter[tags]=X,Y,Z   # The right answer; use the reserved filter family
```

The general principle. **Operations belong in the reserved query family they semantically match.** Filtering goes in `filter[*]`, pagination in `page[*]`, sorting in `sort`, field selection in `fields[*]`. Side-channel custom parameters bypass the conventions that let generic tooling work.

## Related Concepts

- [[json-api/json-api-index]]: graph-protocol mental model
- [[json-api/document-structure]]: envelope, resources, relationships, included
- [[json-api/meta-vs-resource]]: identity test for what becomes a resource
- [[json-api/content-type-and-errors]]: content negotiation and error shape

## References

- [JSON:API v1.1 specification](https://jsonapi.org/format/): sections on Sparse Fieldsets, Pagination, Filtering, Sorting
- [JSON:API recommendations](https://jsonapi.org/recommendations/): non-normative guidance on filter and pagination URL design
- [JSONAPI-Resources filtering](https://github.com/JSONAPI-Resources/jsonapi-resources): concrete operator-style filter implementation
