---
title: Spec layers
aliases:
- API spec layers
- JSON Schema vs OpenAPI vs JSON:API
- API specification stack
- three-layer mental model
tags:
- openapi
- json-schema
- json-api
- api-design
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- The three layers at a glance
- JSON Schema is contained in OpenAPI
- JSON:API is orthogonal to OpenAPI
- When teams ask whether they need both
- Common confusions
last_probed:
- The three layers at a glance
- JSON Schema is contained in OpenAPI
- JSON:API is orthogonal to OpenAPI
- When teams ask whether they need both
- Common confusions
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# Spec layers

Three specs people often confuse because all three involve JSON, APIs, and the word "schema". They live at different layers and answer different questions. The mental model below is what unsticks the "wait, do we need all of these?" question.

## TL;DR

- **JSON Schema** validates a single JSON document.
- **OpenAPI** describes an HTTP API and uses JSON Schema for data shapes.
- **JSON:API** is a payload-shape convention, independent of how the API is described.
- Layering. JSON Schema ⊂ OpenAPI (containment). JSON:API ⊥ OpenAPI (orthogonal, on a different axis).

## The three layers at a glance

```
JSON:API           ← payload convention (what response bodies look like)
   ↑ described by
OpenAPI            ← interface description (paths, verbs, auth, media types)
   uses ↓
JSON Schema        ← per-document validation (the data shape inside any one body)
```

Reading top to bottom, OpenAPI describes what JSON:API constrains, and uses JSON Schema to describe document shapes inside the operations it lists.

| Layer | Unit it describes | Vocabulary | Authoritative spec |
| --- | --- | --- | --- |
| JSON Schema | One JSON document | `type`, `properties`, `required`, combiners | json-schema.org/draft/2020-12 |
| OpenAPI | An HTTP API surface | `paths`, `components`, `security`, `servers` | spec.openapis.org/oas/v3.1.0 |
| JSON:API | The bytes of a request/response body | `data`, `errors`, `included`, `relationships`, `links`, `meta` | jsonapi.org/format |

## JSON Schema is contained in OpenAPI

OpenAPI does not reinvent data validation; it reuses JSON Schema. In 3.1, Schema Objects are JSON Schema 2020-12 documents with a small OAS overlay (`discriminator`, `xml`, `example`, `externalDocs`). See [[openapi/openapi-overview]].

Practical consequence. Schemas authored inside `components.schemas` are reusable. They validate payloads outside the OpenAPI context with any JSON Schema validator. The OpenAPI envelope adds the *interface* layer of paths, verbs, statuses, while the data-shape work stays JSON Schema work.

## JSON:API is orthogonal to OpenAPI

JSON:API is **not** a competitor to OpenAPI. It does not describe endpoints or operations. It standardizes the **wire format**, the rules every request and response body must follow.

Committing to JSON:API means committing to.

- The `data` / `errors` / `meta` / `links` / `included` envelope ([[json-api/document-structure]])
- Resource objects with `{type, id, attributes, relationships}`
- Sparse fieldsets (`?fields[type]=…`), inclusion (`?include=…`), pagination conventions
- Media type `application/vnd.api+json`
- The full-linkage rule for compound documents

None of that describes HTTP topology. A JSON:API service still has paths, verbs, auth, and per-status response variations, which is exactly what OpenAPI describes. The two specs don't compete; they layer.

The JSON:API 1.1 spec makes this explicit with the `describedby` link relation, which points at OpenAPI or JSON Schema documents. JSON:API expects to be described, by OpenAPI, using JSON Schema.

## When teams ask whether they need both

The question "do we need both OpenAPI and JSON:API?" collapses two layers. Reframe into two independent questions.

- **Do we need a payload format convention?** That's the JSON:API question. Without one, every endpoint invents its own envelope, and clients can't reuse logic for pagination, sideloading, errors. JSON:API is one answer; bare REST with custom shapes is another.
- **Do we need a machine-readable description of our HTTP API?** That's the OpenAPI question. Without one, no generated SDKs, no shared linting, no contract testing.

Either can be answered independently. JSON:API plus OpenAPI is common and idiomatic. JSON:API without OpenAPI works but loses tooling. OpenAPI without JSON:API works fine; most OpenAPI APIs aren't JSON:API.

## Common confusions

- **"JSON Schema equals OpenAPI."** No. JSON Schema validates one document; OpenAPI describes a whole API. OpenAPI embeds JSON Schema for data-shape parts but adds an entire HTTP-interface vocabulary on top.
- **"JSON:API equals JSON Schema."** No. JSON:API is a payload-shape convention; JSON Schema is a validation language. You can write a JSON Schema *for* a JSON:API document, describing the envelope and its rules, but they're different specs.
- **"JSON:API is an alternative to OpenAPI."** No. They live at different layers. Use both together, or either alone.
- **"OpenAPI 3.0 schemas are JSON Schema."** Not strictly. 3.0 used a *modified subset* of an older draft. Only 3.1 aligned with mainline JSON Schema (2020-12). See [[openapi/openapi-overview]].
- **"Swagger and OpenAPI are different specs."** No. Same spec, different names across history. Swagger 2.0 (2014) became OpenAPI 3.0 (2017). The "Swagger" brand persists on SmartBear's tools.

## Related Concepts

- [[json-schema/json-schema-overview]]: the validation language at the bottom of the stack
- [[openapi/openapi-overview]]: the description layer in the middle
- [[json-api/document-structure]]: the payload-shape convention beside the stack
- [[openapi/schema-composition]]: composition keywords shared across JSON Schema and OpenAPI

## References

- [json-schema.org](https://json-schema.org/): drafts and dialect alignment with OpenAPI
- [OpenAPI 3.1 specification](https://spec.openapis.org/oas/v3.1.0.html): the description layer
- [JSON:API v1.1 specification](https://jsonapi.org/format/): the payload-shape convention
- [Validating OpenAPI and JSON Schema (json-schema.org blog)](https://json-schema.org/blog/posts/validating-openapi-and-json-schema): the layering relationship from the JSON Schema side
