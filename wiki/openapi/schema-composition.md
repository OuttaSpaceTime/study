---
title: Schema Composition
aliases:
- allOf anyOf oneOf
- JSON Schema combiners
- schema composition keywords
- OpenAPI polymorphism
tags:
- openapi
- json-schema
- api-design
created: '2026-04-09'
updated: '2026-04-09'
source_skill: study-walkthrough
flashcard_ids: []
depth: 1
next_review: '2026-06-07'
review_interval: 8
probe_sections:
- anyOf vs oneOf
- The oneOf Shared-Field Trap
- allOf Is Not Inheritance
- The additionalProperties Trap
- not as a Filter
last_probed:
- The additionalProperties Trap
- not as a Filter
- anyOf vs oneOf
- The oneOf Shared-Field Trap
- allOf Is Not Inheritance
---

# Schema Composition

JSON Schema provides four keywords for combining schemas. OpenAPI inherits all four.

| Keyword | Logic | Rule                                |
| ------- | ----- | ----------------------------------- |
| `allOf` | AND   | Value must match **every** schema   |
| `anyOf` | OR    | Value must match **at least one**   |
| `oneOf` | XOR   | Value must match **exactly one**    |
| `not`   | NOT   | Value must **not** match the schema |

## anyOf vs oneOf

`anyOf` passes when one or more schemas match. It doesn't care about overlap, and validation can short-circuit on the first match. `oneOf` is strict. It must validate the payload against **every** listed schema to confirm exactly one matches. If two or more match, validation fails.

Practical distinction. Use `anyOf` when formats may overlap (e.g., a field accepting ISO date string or Unix timestamp). Use `oneOf` when types are truly exclusive (e.g., polymorphic API responses).

## The oneOf Shared-Field Trap

When schemas under `oneOf` share fields, a minimal payload can accidentally match multiple schemas:

```yaml
oneOf:
  - $ref: '#/components/schemas/CreditCardPayment'   # has amount: number
  - $ref: '#/components/schemas/BankTransferPayment'  # has amount: number
```

A payload with just `"amount"` field matches both schemas. `oneOf` rejects it.

Fix. Add a **discriminator** so each schema has a unique required field.

```yaml
oneOf:
  - $ref: '#/components/schemas/CreditCardPayment'
  - $ref: '#/components/schemas/BankTransferPayment'
discriminator:
  propertyName: payment_type
```

Each schema declares `payment_type` as required with a fixed value (`"credit_card"` or `"bank_transfer"`). The validator can jump directly to the right schema instead of trying all of them.

## allOf Is Not Inheritance

`allOf` means "validate against every listed schema simultaneously." It's often used to extend a base schema, but it's pure composition. Not OOP inheritance.

```yaml
allOf:
  - $ref: '#/components/schemas/BaseEntity'
  - type: object
    properties:
      extra_field:
        type: string
```

The payload must satisfy both schemas. If they define the same property with incompatible types (e.g., `id` as `string` vs `id` as `integer`), no payload can ever validate. This is a silent, schema-level contradiction with no syntax error.

## The additionalProperties Trap

Using `additionalProperties` set to `false` inside `allOf` breaks composition.

```yaml
allOf:
  - type: object
    properties:
      id:
        type: string
    additionalProperties: false
  - type: object
    properties:
      name:
        type: string
```

When `additionalProperties` is set to `false`, it's evaluated per-schema, not on the merged result. The first schema sees `name` as an additional property and rejects it. Even though it's defined in the second schema.

Fix. Lift `additionalProperties: false` out of the inner schemas and onto the composed wrapper, so the constraint applies to the merged shape:

```yaml
type: object
additionalProperties: false
allOf:
  - type: object
    properties:
      id:
        type: string
  - type: object
    properties:
      name:
        type: string
```

Now `{ "id": "abc", "name": "widget" }` validates, and unknown keys still get rejected. The `false` gate evaluates against the union of declared properties, not against each fragment in isolation.

## not as a Filter

`not` rejects values matching a schema. Combined with other keywords it acts as a filter:

```yaml
allOf:
  - $ref: '#/components/schemas/Animal'
  - not:
      required: ['wings']
```

This accepts any valid Animal that does not require `wings`.
