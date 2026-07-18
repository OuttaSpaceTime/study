---
title: Key Derivation and Domain Separation
aliases:
- KDF
- key derivation function
- salt vs secret
- domain separation
- purpose separation
tags:
- security
- cryptography
- no-study
created: '2026-07-18'
updated: '2026-07-18'
source_skill: study-flashcard
flashcard_ids:
- cmrq07c7z000dgl0metdea28f
- cmrq07dca000egl0md1eaxsmd
- cmrq07etm000fgl0m8ceqwt7m
- cmrq07g3m000ggl0mvxnqgddj
- cmne7xtdc015z0msomwlu8l9d
probe_sections:
- 'Secret, salt, and KDF: what each term means'
- Why a KDF stretches instead of concatenating
- 'Encrypting vs signing: confidentiality vs integrity'
- Why reusing one derived key for two purposes weakens both
- The salt does not need to be secret, only the underlying secret does
- Purpose strings in Rails as domain separators
last_probed:
- 'Secret, salt, and KDF: what each term means'
- Why a KDF stretches instead of concatenating
- 'Encrypting vs signing: confidentiality vs integrity'
- Why reusing one derived key for two purposes weakens both
- The salt does not need to be secret, only the underlying secret does
- Purpose strings in Rails as domain separators
review_interval: 3
next_review: '2026-07-21'
---

# Key Derivation and Domain Separation

A single master secret can safely power many independent cryptographic operations. The trick is deriving a separate key per purpose instead of reusing one key everywhere. Rails cookies are a concrete example. One `secret_key_base` backs both the encrypted session cookie and the signed session cookie, without either operation weakening the other.

## Secret, salt, and KDF: what each term means

The **secret** is the one piece of material that must stay confidential, for example `Rails.application.secret_key_base`. The **salt** is a plain, non-secret string that identifies a purpose, like `"encrypted cookie"` or `"signed cookie"`. A **KDF** (Key Derivation Function) combines the two and outputs a **key**, a byte string sized for a specific algorithm.

```ruby
key_generator = ActiveSupport::KeyGenerator.new(secret_key_base)
encryptor_key = key_generator.generate_key("encrypted cookie", 32)
signer_key    = key_generator.generate_key("signed cookie", 64)
```

Same secret, different salts, two unrelated keys.

## Why a KDF stretches instead of concatenating

A KDF like PBKDF2 or HKDF runs the secret and salt through a one-way function many times over, not a single concatenation. Repeated hashing stretches short or weak input into a key of the right length and entropy, and makes brute-forcing the original secret from a leaked key computationally expensive.

## Encrypting vs signing: confidentiality vs integrity

Encryption hides data. It is reversible with the right key, and it protects confidentiality. Signing leaves data fully readable and adds a tamper-proof tag (an HMAC) proving the data has not been altered and came from whoever holds the signing key. It protects integrity and authenticity, not secrecy.

A Rails encrypted cookie cannot be read by the browser or the user. A signed-only cookie is fully readable, but editing a single byte breaks the signature and Rails rejects it.

## Why reusing one derived key for two purposes weakens both

Encryption and signing look like separate features, so it is tempting to use one key for both. That removes the isolation between them. If an attacker can influence or observe one operation (for example a timing leak on the signature check), the information they extract comes from the same key material that also protects the other operation. A weakness found through one path can compromise the other, even though the two features never appear related on the surface.

## The salt does not need to be secret, only the underlying secret does

The salt is a domain separator, not a secret. It could be printed in a public repository with no security impact, because its only job is to make sure deriving a key for purpose A lands on a different output than purpose B, even from the same underlying secret. All the confidentiality lives in the secret itself.

## Purpose strings in Rails as domain separators

Rails token helpers generalize the same salt idea under the name `purpose:`.

```ruby
Rails.application.message_verifier(:password_reset)
Rails.application.message_verifier(:unsubscribe)
```

Both derive from the same `secret_key_base`, but the `purpose:` string is mixed into the derivation just like a salt, so each purpose gets an independent key domain. A token minted for `:unsubscribe` fails verification under the `:password_reset` verifier, even though both trace back to one secret. The same mechanism backs `signed_id(purpose:)` and `generates_token_for`.

## Related Concepts

- [[security/csrf]]: another case where a token must be tied to a specific context, there the session, to stop reuse across requests.
- [[security/hsts]]: a different security header mechanism, useful as a contrast in how browsers versus servers enforce guarantees.
