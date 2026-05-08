---
title: Document structure
aliases:
- JSON:API document
- JSON:API envelope
- JSON:API resource object
- relationships vs included
tags:
- api-design
- json-api
- rest
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- Top-level keys and their mutual exclusions
- Resource object shape
- relationships hold pointers, included holds payloads
- Compound documents and the full-linkage rule
- Every node on an include path is included
last_probed:
- Top-level keys and their mutual exclusions
- Resource object shape
- relationships hold pointers, included holds payloads
- Compound documents and the full-linkage rule
- Every node on an include path is included
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# JSON:API document structure

JSON:API is a graph protocol wearing REST clothes. Every response is a slice of a graph, not a record, and the document envelope reflects that. Once the envelope clicks, every other rule (full linkage, mutual exclusions, the relationships/included split) stops feeling arbitrary.

## TL;DR

- `data` and `errors` are mutually exclusive at the top level. `included` requires `data`.
- Every resource has the same shape wherever it appears: `{type, id, attributes, relationships}`.
- `relationships` holds **resource identifiers** (`{type, id}` pairs only). Full attributes for related resources live in top-level `included`, and only when the client asks via `?include=`.
- Compound documents must satisfy **full linkage**: every resource in `included` is reachable from `data` by walking relationship pointers.
- `?include=a.b.c` includes **every node along the path**, not just the leaf.

## Top-level keys and their mutual exclusions

Five top-level keys. A document MUST contain at least one of `data`, `errors`, `meta`.

| Key        | Purpose                                              |
| ---------- | ---------------------------------------------------- |
| `data`     | The node(s) the client asked for                     |
| `errors`   | Failure list (mutually exclusive with `data`)        |
| `included` | Other graph nodes fetched in the same round-trip     |
| `links`    | Where to walk next (pagination, related resources)   |
| `meta`     | Out-of-band info (counts, request id, debug)         |

Three rules fall out:

1. `data` and `errors` cannot coexist. You are either returning a graph slice or you failed.
2. `included` requires `data`. A graph slice with no entry point is meaningless.
3. `data` is either a single resource object, an array, or `null` (for to-one relationships that resolve to no resource).

## Resource object shape

A resource has the same shape everywhere (top-level `data`, inside an array, or inside `included`):

```json
{
  "type": "articles",
  "id": "1",
  "attributes": {
    "title": "Why JSON:API is a graph protocol",
    "created_at": "2026-05-01T10:00:00Z"
  },
  "relationships": {
    "author": { "data": { "type": "people", "id": "9" } },
    "comments": { "data": [
      { "type": "comments", "id": "5" },
      { "type": "comments", "id": "12" }
    ]}
  },
  "links": { "self": "/articles/1" },
  "meta": { "version": 3 }
}
```

Three rules:

- `type` and `id` are both **strings** and both **required** on every resource. (`id` may be omitted only when a client is creating a brand-new resource.)
- `attributes`, `relationships`, `type`, and `id` share **one namespace**, with no key collisions. You cannot have an attribute named `type` or a relationship named `id`.
- v1.1 added `lid` (local id) for client-generated identifiers in atomic operations. Useful when creating multiple linked resources in one request.

## relationships hold pointers, included holds payloads

This is the single most-misunderstood piece of the spec.

- **`relationships`** lives *inside* a resource object. Each member contains a `data` field that holds **resource identifiers only**, i.e. `{type, id}` pairs. Think of it as a foreign key, not a join.
- **`included`** lives at the *top level* of the document. It holds **full resource objects** for related resources the client asked for via `?include=`.

Without `?include=author`, the `included` array is absent. But `relationships.author.data` is still there. Clients always know *what* the author is; they only know the author's *attributes* if they asked.

```json
{
  "data": {
    "type": "articles", "id": "1",
    "attributes": { "title": "..." },
    "relationships": {
      "author": { "data": { "type": "people", "id": "9" } }
    }
  },
  "included": [
    { "type": "people", "id": "9",
      "attributes": { "name": "Dan" } }
  ]
}
```

The split exists so the relationship graph (cheap, always present) is decoupled from attribute payloads (expensive, opt-in). Generic clients can render relationship structure without fetching anything they did not ask for.

## Compound documents and the full-linkage rule

A document with `included` is a **compound document**. Two rules govern it:

1. **Full linkage**: every resource in `included` MUST be reachable from `data` by walking relationship pointers. No orphans. The exception is sparse fieldsets that strip the relationship members linking back to the included resources, but in normal use full linkage holds.
2. **Deduplication**: `included` is a set keyed on `(type, id)`. A resource that appears via two different paths (e.g. an author who also wrote a comment) appears **once**, not twice.

These together mean clients reconstruct the full graph by following `relationships.X.data → {type, id}` pointers back into `included`, which is just a flat lookup table. No tree traversal, no nested payloads.

## Every node on an include path is included

`?include=` takes comma-separated relationship paths, with dots for nesting:

```
GET /articles?include=author,comments.author
```

**Every node along the path** is included, not just the leaf. So `?include=comments.author` returns:

- the comments themselves (intermediate node)
- the comments' authors (leaf)

This is the silent-payload-inflation trap. A long include chain (`?include=organization.team.lead.manager`) returns four resource types in `included`, deduplicated but each carrying full attributes. Audit deep includes before exposing them.

## Related Concepts

- [[json-api/json-api-index]]: graph-protocol mental model
- [[json-api/query-conventions]]: sparse fieldsets, pagination, filter, sort
- [[json-api/meta-vs-resource]]: identity test for what belongs where
- [[json-api/content-type-and-errors]]: operational details

## References

- [JSON:API v1.1 specification](https://jsonapi.org/format/): official current spec
- [JSON:API v1.0 specification](https://jsonapi.org/format/1.0/): archived previous version, useful for diffing
- [JSON:API recommendations](https://jsonapi.org/recommendations/): non-normative guidance on URL design
- [JSONAPI-Resources (Ruby)](https://github.com/JSONAPI-Resources/jsonapi-resources): canonical Rails implementation, useful as a reference for how the spec gets operationalised
