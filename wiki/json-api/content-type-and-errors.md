---
title: Content type and errors
aliases:
- application/vnd.api+json
- JSON:API content negotiation
- JSON:API error object
- JSON:API source.pointer
tags:
- api-design
- json-api
- rest
- http
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- The content type and what 415 vs 406 mean
- Error object shape and the string status quirk
- source.pointer maps errors back to request fields
- Multiple errors per response
last_probed:
- The content type and what 415 vs 406 mean
- Error object shape and the string status quirk
- source.pointer maps errors back to request fields
- Multiple errors per response
depth: 1
review_interval: 3
next_review: '2026-05-11'
---

# JSON:API content type and errors

Two operational details trip every team building a JSON:API API. Content type negotiation, and the structured error object. Both are worth getting right because they unlock generic client behaviour (form binding, error display, content-type-aware proxies).

## TL;DR

- Always send `Content-Type: application/vnd.api+json` and `Accept: application/vnd.api+json`. Only `ext` and `profile` parameters are permitted on the media type.
- Wrong `Content-Type` parameters → server MUST `415`. No acceptable `Accept` variant → server MUST `406`.
- Errors live in a top-level `errors` array, mutually exclusive with `data`. `status` is a **string**, not a number.
- `source.pointer` is a JSON Pointer (RFC 6901) into the request body. It is what makes generic form-binding clients work.
- Return all validation errors at once. Multiple error objects per response is encouraged.

## The content type and what 415 vs 406 mean

```http
POST /articles HTTP/1.1
Content-Type: application/vnd.api+json
Accept:       application/vnd.api+json
```

Per spec, the only allowed media-type parameters are `ext` (extensions) and `profile` (v1.1 profiles). Anything else is non-compliant.

Two HTTP status codes you must return correctly:

- **`415 Unsupported Media Type`**: client sent `Content-Type: application/vnd.api+json; <unsupported-param>`.
- **`406 Not Acceptable`**: every variant in the client's `Accept` header carries unsupported parameters (or no compatible variant exists).

The common failure. Returning `Content-Type: application/json` to be "compatible" with non-JSON:API clients. Strict JSON:API clients will reject this. If you serve JSON:API, send the JSON:API content type. Co-host a non-JSON:API endpoint at a different path if you need raw JSON elsewhere.

## Error object shape and the string status quirk

`errors` is a top-level array, mutually exclusive with `data`:

```json
{
  "errors": [
    {
      "status": "422",
      "code":   "invalid_email",
      "title":  "Validation failed",
      "detail": "must be a valid email address",
      "source": { "pointer": "/data/attributes/email" },
      "meta":   { "field": "email" }
    }
  ]
}
```

All members are optional, but a useful error object includes:

| Member    | Purpose                                                        |
| --------- | -------------------------------------------------------------- |
| `status`  | HTTP status code as a **string** (spec quirk, not a number)   |
| `code`    | Application-specific error code, stable across messages        |
| `title`   | Human-readable summary, generic across instances of this error |
| `detail`  | Specific human-readable explanation for this occurrence        |
| `source`  | `pointer` (JSON Pointer into request body) or `parameter`      |
| `meta`    | Anything else (field name, retry-after, etc.)                  |
| `id`      | Unique identifier for this particular occurrence (for support) |

The string-`status` quirk catches everyone once. The reasoning is that error objects carry application-defined status semantics independent of the HTTP layer, but in practice it just means "remember to stringify."

## source.pointer maps errors back to request fields

`source.pointer` is a [RFC 6901 JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) into the request body. For a request like:

```json
{
  "data": {
    "type": "users",
    "attributes": {
      "email": "not-an-email",
      "name": ""
    }
  }
}
```

…the corresponding errors:

```json
{
  "errors": [
    { "source": { "pointer": "/data/attributes/email" },
      "detail": "must be a valid email address" },
    { "source": { "pointer": "/data/attributes/name" },
      "detail": "cannot be blank" }
  ]
}
```

This is what lets generic form-binding clients map errors back to UI fields automatically. The same JSON Pointer that addresses `email` in the request body addresses the error's source. The client does not need API-specific glue.

For query-parameter errors (e.g. unknown sort field, invalid filter syntax), use `source.parameter` instead:

```json
{ "errors": [{ "source": { "parameter": "sort" },
               "detail": "unknown sort field 'foo'" }] }
```

## Multiple errors per response

Multiple error objects per response is **encouraged** for validation. Return all field errors at once rather than one at a time:

- Better UX: the user sees every problem in a single round-trip.
- Better debuggability: your logs show the full set, not "user fixed first error, server returned the second, repeat".
- Spec-aligned: the `errors` array exists precisely for this.

The HTTP status code in the response is the most-applicable single code (typically `422` for validation, `400` for malformed request). The per-error `status` strings can vary if the errors span different categories.

## Related Concepts

- [[json-api/json-api-index]]: graph-protocol mental model
- [[json-api/document-structure]]: top-level keys and the data/errors mutual exclusion
- [[json-api/query-conventions]]: when `source.parameter` is the right field

## References

- [JSON:API v1.1, Content Negotiation](https://jsonapi.org/format/#content-negotiation): official rules for media type and parameters
- [JSON:API v1.1, Errors](https://jsonapi.org/format/#errors): error object members and semantics
- [RFC 6901, JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901): the addressing syntax used by `source.pointer`
