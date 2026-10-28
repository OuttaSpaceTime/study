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
created: '2026-07-18'
updated: '2026-10-25'
source_skill: study-flashcard
flashcard_ids:
- cmrq07c7z000dgl0metdea28f
- cmrq07dca000egl0md1eaxsmd
- cmrq07etm000fgl0m8ceqwt7m
- cmne7xtdc015z0msomwlu8l9d
- cmvnnuvct0000cl1a6uswfhrf
- cmvnnuwqp0001cl1asvz5qoap
- cmvnnuxza0002cl1audfwuflg
- cmvno7tt80003cl1ai8exu6tt
---

# Key Derivation and Domain Separation

A single master secret can safely power many independent cryptographic operations. The trick is deriving a separate key per purpose instead of reusing one key everywhere. Rails cookies are a concrete example. One `secret_key_base` backs both the encrypted session cookie and the signed session cookie, without either operation weakening the other.

## Secret, Salt, and KDF: What Each Term Means

The **secret** is the one piece of material that must stay confidential, for example `Rails.application.secret_key_base`. The **salt** is a plain, non-secret string mixed into the derivation, like `"authenticated encrypted cookie"` or `"signed cookie"`. A **KDF** (Key Derivation Function) combines the two and outputs a **key**, a byte string sized for a specific algorithm.

```ruby
key_generator = Rails.application.key_generator   # PBKDF2 over secret_key_base
encryptor_key = key_generator.generate_key("authenticated encrypted cookie", 32)  # AES-256-GCM
signer_key    = key_generator.generate_key("signed cookie")                       # default size 64
```

Same secret, different salts, two unrelated keys. These are the salts Rails uses for its cookie jars. `"encrypted cookie"` is the older salt for the legacy AES-256-CBC cookies, which Rails still reads during an upgrade.

## Two KDF Families: Slow for Passwords, Fast for Strong Secrets

All KDFs are one-way and turn input into a key of the needed length. They split on whether they are deliberately slow.

- **Password KDFs** (PBKDF2, bcrypt, scrypt, Argon2): slow on purpose, so each guess costs the attacker real work. They exist for low-entropy, human-chosen secrets.
- **Fast KDFs** (HKDF): one extract step and one expand step, no stretching. They exist for input that is already high-entropy, like a random master key or a Diffie-Hellman shared secret.

Stretching only pays off when the attacker can enumerate the likely secrets. Human passwords fall into maybe 10^7 plausible guesses, so 100,000 rounds per guess turns a quick crack into a long one. A random 512-bit `secret_key_base` has 2^512 possibilities, so brute force is infeasible before any stretching. There the KDF's only job is deriving separate keys per purpose.

RFC 5869 says this directly. HKDF's extract step "can concentrate existing entropy but cannot amplify entropy", a slowing mechanism is not part of HKDF, and applications that need a password-based KDF should consider PKCS #5 (PBKDF2) instead.

## How PBKDF2 Stretches a Password

PBKDF2 chains HMAC calls and folds the results together with XOR. For output block 1 with `c` iterations:

```text
U1 = HMAC(key = secret, msg = salt || INT(1))
U2 = HMAC(key = secret, msg = U1)
...
Uc = HMAC(key = secret, msg = U(c-1))
block1 = U1 xor U2 xor ... xor Uc
```

The secret is the HMAC key in every round. If it entered only the first round, anyone holding `U1` could finish the chain without knowing the password. The rounds are sequential, because each one needs the previous output, so an attacker pays all `c` rounds for every guess. A longer key means more blocks, computed the same way with counter 2, 3 and so on, concatenated and truncated to the requested length.

## The Salt Plays Two Roles, Neither Secret

The salt is never the confidential part. It could be printed in a public repository with no security impact. What it must be depends on the family.

- **Password hashing**: a random salt per user. Without one, equal passwords produce equal stored hashes. Cracking one user cracks everyone who shares that password, and precomputed tables work against the whole table. A per-user salt makes each guess usable against one user only.
- **Domain separation**: a fixed public label per purpose, like `"signed cookie"`. Its job is to make purpose A derive a different key than purpose B from the same secret.

All the confidentiality lives in the secret itself.

## Both Families in Rails

`has_secure_password` uses bcrypt, the password family. Each user gets a random salt, and bcrypt stores the algorithm version, cost and salt next to the hash in the `password_digest` column.

```text
$2a$12$<22-char salt><31-char hash>
 |   |
 |   cost 12, so 2^12 rounds of the key schedule
 bcrypt version
```

Verifying a login reads the salt and cost back out of the digest and repeats the work.

`Rails.application.key_generator` is PBKDF2-HMAC over `secret_key_base`, the domain-separation use. It runs only 1000 iterations, because the input is already random and stretching would buy nothing. Apps on `load_defaults 7.0` or later use SHA-256 as its digest; older defaults use SHA-1.

## Encrypting vs Signing: Confidentiality vs Integrity

Encryption hides data. It is reversible with the right key, and it protects confidentiality. Signing leaves data fully readable and adds a tamper-proof tag (an HMAC) proving the data has not been altered and came from whoever holds the signing key. It protects integrity and authenticity, not secrecy.

A Rails encrypted cookie cannot be read by the browser or the user. A signed-only cookie is fully readable, but editing a single byte breaks the signature and Rails rejects it.

## Why Reusing One Derived Key for Two Purposes Weakens Both

Encryption and signing look like separate features, so it is tempting to use one key for both. That removes the isolation between them. If an attacker can influence or observe one operation (for example a timing leak on the signature check), the information they extract comes from the same key material that also protects the other operation. A weakness found through one path can compromise the other, even though the two features never appear related on the surface.

## Purpose Strings in Rails as Domain Separators

Rails token helpers separate purposes at two levels. The verifier name is a salt.

```ruby
Rails.application.message_verifier(:password_reset)
Rails.application.message_verifier(:unsubscribe)
```

Rails passes each name to `key_generator.generate_key` as the salt, so each verifier gets its own key from the same `secret_key_base`. A token minted by the `:unsubscribe` verifier fails verification under the `:password_reset` verifier.

The `purpose:` option is a lighter mechanism. It does not change the key. It is written into the signed message and checked on verify, so a token generated with one purpose is rejected under another even though one verifier signs both. `signed_id(purpose:)` and `generates_token_for` work this way.

## Sources

- [RFC 5869, section 4](https://www.rfc-editor.org/rfc/rfc5869#section-4): HKDF cannot amplify entropy and has no slowing mechanism.
- [`Rails::Application#key_generator`](https://github.com/rails/rails/blob/main/railties/lib/rails/application.rb): PBKDF2 key generator with 1000 iterations.
- [`ActiveSupport::KeyGenerator`](https://github.com/rails/rails/blob/main/activesupport/lib/active_support/key_generator.rb): `generate_key(salt, key_size = 64)` calls `OpenSSL::PKCS5.pbkdf2_hmac`.
- [`action_dispatch/railtie.rb`](https://github.com/rails/rails/blob/main/actionpack/lib/action_dispatch/railtie.rb): the cookie salt defaults.

## Related Concepts

- [[security/csrf]]: another case where a token must be tied to a specific context, there the session, to stop reuse across requests.
- [[security/hsts]]: a different security header mechanism, useful as a contrast in how browsers versus servers enforce guarantees.
