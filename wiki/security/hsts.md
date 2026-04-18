---
title: HSTS
aliases:
- HTTP Strict Transport Security
- Strict-Transport-Security header
- HSTS preload
tags:
- security
- https
- web
created: '2026-04-10'
updated: '2026-04-10'
source_skill: study-walkthrough
flashcard_ids:
- cmne7xvvx01sd0mso4nghg03i
- cmne7xw1v01u10msoxw2b49vt
- cmne7xw2401u30msofm43aa2a
- cmne7xvym01t50msou805xi7h
- cmne7xwri02050mso5k9tqzu4
depth: 1
next_review: '2026-04-23'
review_interval: 5
---

# HSTS (HTTP Strict-Transport-Security)

HSTS is a response header that tells browsers to **never send HTTP requests** to a domain — convert them to HTTPS internally before any network traffic. It defends against SSL stripping attacks where an attacker intercepts the first plaintext HTTP request.

## The SSL Stripping Attack

Without HSTS, typing `example.com` sends a plaintext `GET http://example.com`. An attacker on the same network (e.g. public WiFi) can:

1. Intercept the plaintext HTTP request
2. Connect to `https://example.com` on the victim's behalf
3. Relay content back over HTTP, stripping all HTTPS references
4. The victim sees a working site. The attacker sees all traffic

The server's 301 redirect to HTTPS never reaches the victim.

## The Header

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

- **`max-age`** — how long (in seconds) the browser remembers the rule. Recommended: 2 years (63072000s).
- **`includeSubDomains`** — applies HSTS to all subdomains.
- **`preload`** — opts into the browser preload list.

The header **must be served over HTTPS** — browsers ignore it over HTTP (otherwise an attacker could forge it).

## TOFU Problem (Trust On First Use)

HSTS only protects after the browser has seen the header once. The very first visit is still vulnerable — the browser doesn't yet know to upgrade. This gap is the TOFU problem.

Other TOFU examples: SSH host fingerprints are trusted blindly on first connection.

## Preload

Adding `preload` and submitting the domain to the HSTS preload list solves TOFU. The list is **hardcoded into browser binaries** (Chrome, Firefox, Safari share one). The browser enforces HTTPS before ever visiting the site.

**Tradeoff:** preload is effectively permanent. Removal takes months (submit request → wait for processing → wait for browser releases → wait for user updates). Every subdomain must support HTTPS — any subdomain without a valid TLS certificate becomes completely inaccessible (hard browser error, no workaround).

## Cross-Host Redirects

```
http://example.com → https://www.example.com    ← BROKEN
```

The HSTS header from `www.example.com` only protects `www.example.com`. The bare domain `example.com` never served HSTS over HTTPS, so `http://example.com` remains vulnerable on **every** visit — not just the first.

**Fix — redirect same-host first:**

```
http://example.com → https://example.com → https://www.example.com
```

The middle hop lets `example.com` serve its own HSTS header. This reduces the vulnerability to the TOFU problem (first visit only). Full protection still requires `preload`.

## Full Defense Stack

1. **Same-host HTTPS redirect** — each domain serves its own HSTS header
2. **HSTS with `max-age` + `includeSubDomains`** — protects returning visitors
3. **`preload`** — protects first-time visitors
