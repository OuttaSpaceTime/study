---
title: JSON Schema overview
aliases:
- json-schema basics
- what is JSON Schema
- json-schema vocabulary
tags:
- json-schema
- api-design
- validation
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- A predicate vocabulary, not a type definition
- What JSON Schema does not describe
- Drafts and dialect drift
- Null via type lists and keyword type-relativity
- Where it shows up beyond APIs
last_probed:
- A predicate vocabulary, not a type definition
- What JSON Schema does not describe
- Drafts and dialect drift
- Null via type lists and keyword type-relativity
- Where it shows up beyond APIs
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# JSON Schema overview

JSON Schema is an instance-validation language. Given a JSON value (the *instance*) and a schema, it answers one question. Does this value conform? It is written in JSON, has no notion of HTTP, and predates the API-spec ecosystem that now embeds it.

## TL;DR

- JSON Schema validates a single JSON document. It does **not** describe an API.
- A schema is a *set of predicates*, not a type definition. `{}` accepts every value; `{ "not": {} }` rejects every value.
- Latest draft is **2020-12**. Older drafts (4, 7, 2019-09) are still in use. Dialects are not interchangeable.
- Inside OpenAPI 3.1, the Schema Object **is** a JSON Schema 2020-12 document plus a small OAS overlay.

## A predicate vocabulary, not a type definition

Schemas don't declare types in the way TypeScript or Java do. They stack constraints. Each keyword (`type`, `properties`, `required`, `minimum`, `pattern`, `enum`, `allOf`, `anyOf`, `oneOf`, `not`) is a predicate. A yes/no test against the instance. The combiners exist as first-class keywords because schemas compose by AND/OR/XOR over predicates, not by inheritance.

This is why the same schema can describe wildly different shapes (`anyOf: [...]`) without any class hierarchy, and why "extending a schema" usually means `allOf: [base, additional]` rather than subclassing. See [[openapi/schema-composition]] for the four combiners and their gotchas.

## What JSON Schema does not describe

- HTTP verbs, paths, status codes, content types
- Authentication or authorization
- Server URLs, versioning, deprecation
- Anything about the *transport* between client and server

These are OpenAPI's job. JSON Schema knows about a single document; OpenAPI knows about an API. See [[openapi/openapi-overview]] for the layer above.

## Drafts and dialect drift

JSON Schema has gone through several drafts. The major ones still in the wild:

| Draft | Year | Notable trait |
| --- | --- | --- |
| Draft 4 | 2013 | Boolean `exclusiveMinimum`, `id` (no `$`) |
| Draft 7 | 2018 | `$id`, `if`/`then`/`else`, `const` |
| 2019-09 | 2019 | Vocabularies, `$defs` (replaces `definitions`) |
| 2020-12 | 2020 | Tuple/array split (`prefixItems`), aligns with OpenAPI 3.1 |

Tooling typically pins to one draft. Mixing drafts in one project is a known source of "this validates here but not there" bugs. The `$schema` keyword declares which draft a document targets; under 2020-12 it can vary per-schema inside a larger document.

## Null via type lists and keyword type-relativity

Two foundational rules catch newcomers.

**`type` accepts a list.** `{ "type": ["integer", "null"] }` validates both integers and the literal `null`. There is no `nullable: true` keyword in JSON Schema. That was an OpenAPI 3.0 invention that 3.1 dropped (see [[openapi/openapi-overview]]).

**Keywords are type-relative.** `minimum: 0` only constrains numbers. Against `null`, against a string, against an array, `minimum` is silently inert. By design. Schemas validate what *applies* to the instance type. A schema can therefore attach number constraints, string constraints, and array constraints all at once, and only the relevant ones fire for a given instance.

## Where it shows up beyond APIs

JSON Schema predates the API-spec ecosystem and is used widely outside HTTP:

- **Configuration validation**. `package.json`, `tsconfig.json`, GitHub Actions workflows, JetBrains and VS Code settings, Helm chart `values.schema.json`
- **Form generation**. Render UIs from schemas (`react-jsonschema-form`, JSON Forms)
- **Data pipelines**. Describing event payloads in Kafka schemas, log shapes, ETL inputs
- **Standalone instance validation**. Ajv, jsonschema, json-schema-validator

API spec usage (via OpenAPI) is one important consumer, not the canonical one. Treating JSON Schema as "an OpenAPI thing" understates its scope.

## Related Concepts

- [[openapi/schema-composition]]: the `allOf/anyOf/oneOf/not` combiners with their traps
- [[openapi/openapi-overview]]: the API-description layer that embeds JSON Schema
- [[openapi/spec-layers]]: how JSON Schema, OpenAPI, JSON:API stack together
- [[json-api/document-structure]]: JSON:API payload shape, which can itself be described by a JSON Schema

## References

- [JSON Schema 2020-12 core specification](https://json-schema.org/draft/2020-12/json-schema-core): current core spec
- [JSON Schema 2020-12 validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation): keyword definitions (`type`, `minimum`, etc.)
- [json-schema.org](https://json-schema.org/): drafts, tooling list, learning material
