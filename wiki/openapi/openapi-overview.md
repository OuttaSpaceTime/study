---
title: OpenAPI overview
aliases:
- what is OpenAPI
- OpenAPI Specification
- OAS overview
tags:
- openapi
- api-design
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- An OpenAPI document describes an HTTP API
- Top-level keys (paths, components, security)
- Schema Object equals JSON Schema 2020-12 plus OAS overlay
- The OAS overlay (discriminator, xml, example, externalDocs)
- OpenAPI 3.0 to 3.1 drift
- Naming history (Swagger vs OpenAPI)
- Tooling roles (author, render, generate, validate)
last_probed:
- An OpenAPI document describes an HTTP API
- Top-level keys (paths, components, security)
- Schema Object equals JSON Schema 2020-12 plus OAS overlay
- The OAS overlay (discriminator, xml, example, externalDocs)
- OpenAPI 3.0 to 3.1 drift
- Naming history (Swagger vs OpenAPI)
- Tooling roles (author, render, generate, validate)
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# OpenAPI overview

OpenAPI is a specification for describing HTTP APIs as a machine-readable YAML or JSON document. It covers endpoints, verbs, parameters, request and response shapes, and auth. It does not implement an API; it describes one. The spec abbreviates as **OAS** (OpenAPI Specification).

## TL;DR

- OpenAPI = HTTP-API description vocabulary plus embedded JSON Schema for data shapes.
- In **3.1**, the Schema Object is JSON Schema 2020-12 plus a small OAS overlay (`discriminator`, `xml`, `example`, `externalDocs`).
- In **3.0**, the Schema Object was a *modified subset* of an older JSON Schema draft, with incompatibilities like `nullable`, boolean `exclusiveMinimum`, singular `example`.
- The spec is just YAML or JSON. Tools cluster into four roles. Author, render, generate, validate.

## An OpenAPI document describes an HTTP API

The unit OpenAPI describes is the *interface* between client and server. Which paths exist, which HTTP verbs they accept, what goes in path/query/header/cookie parameters, what request bodies and responses (per status code, per media type) look like, what auth schemes apply.

Stripped of data-shape details, an OpenAPI document is a sitemap of operations. The data-shape details, the schemas, are JSON Schema documents nested inside.

## Top-level keys (paths, components, security)

The structural keys at the root of an OpenAPI document.

| Key | Holds |
| --- | --- |
| `info` | API metadata (title, version, description) |
| `servers` | Base URLs |
| `paths` | The endpoints, keyed by URL template (`/users/{id}`); each entry holds verbs (`get`, `post`, …) |
| `components` | Reusable pieces (`schemas`, `parameters`, `responses`, `securitySchemes`) |
| `security` | Default auth requirements |
| `tags` | Grouping for docs |

The most-used corners are `paths.<route>.<verb>.requestBody.content.<media-type>.schema` and `paths.<route>.<verb>.responses.<status>.content.<media-type>.schema`. These `schema:` slots are the seam where JSON Schema lives.

## Schema Object equals JSON Schema 2020-12 plus OAS overlay

In OpenAPI 3.1, [the Schema Object is a JSON Schema 2020-12 vocabulary](https://spec.openapis.org/oas/3.1/dialect/2024-11-10.html). Any valid JSON Schema 2020-12 document is a valid OpenAPI 3.1 schema. The default dialect is `https://spec.openapis.org/oas/3.1/dialect/base`, which is JSON Schema 2020-12 plus OAS-specific keywords.

Practical implication. Schemas can be authored, reviewed, and reused independently of the OpenAPI envelope. A `User` schema written for an OpenAPI doc is also a valid standalone JSON Schema you can validate payloads against directly.

## The OAS overlay (discriminator, xml, example, externalDocs)

Four keywords the OpenAPI Schema Object adds on top of plain JSON Schema 2020-12.

- **`discriminator`**. Pairs with `oneOf`/`anyOf` to tell tooling "look at field `kind` to decide which branch this is." Pure JSON Schema validators ignore it; OpenAPI codegen tools use it to generate sum types.
- **`xml`**. XML serialization hints (attribute vs. element, namespace).
- **`example`**. A single example value, alongside JSON Schema's `examples` array.
- **`externalDocs`**. Link to external documentation.

These are the "this YAML is OpenAPI, not raw JSON Schema" tells.

## OpenAPI 3.0 to 3.1 drift

The migration trap. 3.0's Schema Object was a *modified subset* of an older JSON Schema draft (Wright Draft 05). 3.1 fixed the divergence by adopting JSON Schema 2020-12 outright. The four concrete changes.

| 3.0 | 3.1 (= JSON Schema 2020-12) |
| --- | --- |
| `nullable: true` (boolean alongside `type: string`) | `type: ["string", "null"]` |
| `minimum: 7` + `exclusiveMinimum: true` | `exclusiveMinimum: 7` |
| `example: <single value>` | `examples: [<value>, ...]` |
| `$schema` not allowed in Schema Object | `$schema` allowed per-schema |

> [Warning] The danger is silent. When a 3.0 spec with `nullable: true` is parsed by 3.1 tooling, `nullable` is an unknown keyword and is **silently ignored**. `null` values get rejected by `type: string`. No tool errors, no migration warning. Every nullable field rots into a validation failure in production.

See [the official upgrade guide](https://learn.openapis.org/upgrading/v3.0-to-v3.1.html) for the full migration list.

## Naming history (Swagger vs OpenAPI)

"Swagger" was the original project, started in 2010. Swagger 2.0 (2014) was the most-used pre-3.0 version. In 2016 the project was donated to the Linux Foundation and renamed **OpenAPI Specification** starting at 3.0. SmartBear retained the "Swagger" brand for its tools.

Today, **OpenAPI** is the spec, while **Swagger** is SmartBear's tool family (Swagger Editor, Swagger UI, Swagger Codegen) which now consumes *OpenAPI* documents. Calling the spec "Swagger" is anachronistic but very common.

## Tooling roles (author, render, generate, validate)

OpenAPI tooling clusters into four roles, useful for cutting through marketing pages.

- **Author**. Editor with live spec validation; you write the YAML or JSON and it tells you when it's broken. Some include linters for style and naming rules.
- **Render**. Turn the spec into browsable human docs.
- **Generate**. Turn the spec into typed client SDKs or server stubs.
- **Validate instances**. At runtime, check actual payloads against the schemas extracted from the spec.

There is no "official" OpenAPI tool. The spec is a YAML or JSON file; pick tools that fit your stack.

## Related Concepts

- [[json-schema/json-schema-overview]]: the validation language OpenAPI embeds
- [[openapi/schema-composition]]: `allOf/anyOf/oneOf/not` inside Schema Objects
- [[openapi/spec-layers]]: how OpenAPI relates to JSON:API and JSON Schema
- [[json-api/document-structure]]: JSON:API payload shape (often described by an OpenAPI doc)

## References

- [OpenAPI 3.1.0 specification](https://spec.openapis.org/oas/v3.1.0.html): the current spec
- [OpenAPI 3.1 base dialect](https://spec.openapis.org/oas/3.1/dialect/2024-11-10.html): declares Schema Object = JSON Schema 2020-12 + OAS vocabulary
- [3.0 to 3.1 upgrade guide](https://learn.openapis.org/upgrading/v3.0-to-v3.1.html): concrete migration list
- [openapis.org](https://www.openapis.org/): OpenAPI Initiative landing page
