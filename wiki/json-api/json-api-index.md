---
title: JSON:API Index
aliases:
- json-api-moc
- JSON:API map
- JSON:API mental model
tags:
- moc
- json-api
- api-design
- rest
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
allow_orphan: true
probe_sections:
- The mental model, graph protocol wearing REST clothes
- The envelope-vs-strategy throughline
- When to reach for JSON:API vs GraphQL vs plain REST
- Pages
last_probed:
- The mental model, graph protocol wearing REST clothes
- The envelope-vs-strategy throughline
- When to reach for JSON:API vs GraphQL vs plain REST
- Pages
---

# JSON:API Index

Entry point for the JSON:API reference set. The sub-pages cover document structure, query conventions, the meta-vs-resource decision, and operational details. This page carries the mental model so the others stay focused on practical reference.

## The mental model, graph protocol wearing REST clothes

Every JSON:API response is **a slice of a graph**, not a record. The response envelope reflects that.

```
{
  "data":     "the node(s) you asked for",
  "included": "other nodes reachable from data",
  "links":    "where to walk next",
  "meta":     "out-of-band info",
  "errors":   "mutually exclusive with data"
}
```

Once that frame clicks, every other rule falls out of it:

- `data` and `errors` cannot coexist. A graph slice or a failure, not both.
- `included` requires `data`: a graph fragment with no entry point is meaningless.
- Every resource has the same shape (`{type, id, attributes, relationships}`) wherever it appears (top-level, in arrays, or in `included`).
- `relationships` holds **pointers**, `included` holds **payloads**. Clients walk pointers back into the flat `included` lookup.
- `?include=` walks declared relationship paths only, not arbitrary attributes.

JSON:API takes REST seriously. It commits to one envelope shape so generic clients (caching layers, deserialisers, dev tools) can work uniformly across any compliant API.

## The envelope-vs-strategy throughline

The recurring meta-rule across the spec:

- **Envelope is the contract.** Response shape, top-level keys, resource object shape, error object shape, content type, the reserved query-parameter families (`fields`, `include`, `page`, `filter`, `sort`).
- **Strategy inside reserved families is yours.** Pagination strategy (offset / cursor / page-number), filter syntax, which attributes are sortable, which extensions you support.

This split is deliberate. Uniformity buys generic tooling where it pays off (response shape, family namespaces) and stays out of the way where one-size-fits-all causes more pain than it solves (filter syntax, pagination strategy).

**One heuristic that decides most JSON:API design questions:** the response shape is the contract; the URL grammar inside reserved families is yours.

## When to reach for JSON:API vs GraphQL vs plain REST

| Axis              | JSON:API                                           | GraphQL                                              | Plain REST                |
| ----------------- | -------------------------------------------------- | ---------------------------------------------------- | ------------------------- |
| Field selection   | Per-type (`fields[type]`, global within document)  | Per-path (each branch independent)                   | None, return everything   |
| Schema            | None mandated; v1.1 profiles for extensions        | Strongly typed schema with introspection             | None                      |
| Transport         | RESTful, many URLs, plays with HTTP caching        | Usually one POST endpoint, breaks HTTP caching       | RESTful                   |
| Validation        | Spec says `400` on unknown reserved members; impl varies | Server validates query against schema before exec    | None                      |
| Best fit          | CRUD over a stable resource graph; HTTP caching    | Frontend-driven UIs needing per-screen field sets    | Simple, ad-hoc endpoints  |

**Reach for JSON:API when:** you have a stable resource graph, multiple consumers (web + mobile + integrations), and you want HTTP caching, ETags, and predictable response shapes without bespoke per-endpoint conventions.

**Reach past it (toward GraphQL) when:** field selection needs to be per-edge, schema introspection matters, or you are aggregating across services.

**Stay with plain REST when:** the API is small, single-consumer, or shape stability is not worth the spec ceremony.

## Pages

- [[json-api/content-type-and-errors]]
- [[json-api/document-structure]]
- [[json-api/meta-vs-resource]]
- [[json-api/query-conventions]]

## Related Concepts

- [[openapi/openapi-index]]: sibling API specification topic (schema description language, complementary rather than competing with JSON:API)

## References

- [JSON:API v1.1 specification](https://jsonapi.org/format/): the official current spec
- [JSON:API v1.0 specification](https://jsonapi.org/format/1.0/): archived previous version
- [JSON:API recommendations](https://jsonapi.org/recommendations/): non-normative URL design guidance
- [JSONAPI-Resources (Ruby)](https://github.com/JSONAPI-Resources/jsonapi-resources): canonical Rails implementation
