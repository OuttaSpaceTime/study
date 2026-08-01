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
updated: '2026-05-30'
source_skill: study-walkthrough
flashcard_ids:
- cmne7xvvx01sd0mso4nghg03i
- cmne7xw1v01u10msoxw2b49vt
- cmne7xw2401u30msofm43aa2a
- cmne7xvym01t50msou805xi7h
- cmne7xwri02050mso5k9tqzu4
next_review: '2026-11-03'
review_interval: 95
---

# HSTS (HTTP Strict-Transport-Security)

HSTS is a response header that tells browsers to **never send HTTP requests** to a domain. Convert them to HTTPS internally before any network traffic. It defends against SSL stripping attacks where an attacker intercepts the first plaintext HTTP request.

## The SSL Stripping Attack

Without HSTS, typing `example.com` sends a plaintext `GET http://example.com`. An attacker on the same network (e.g. public WiFi) can:

1. Intercept the plaintext HTTP request
2. Connect to `https://example.com` on the victim's behalf
3. Relay content back over HTTP, stripping all HTTPS references
4. The victim sees a working site. The attacker sees all traffic

The server's 301 redirect to HTTPS never reaches the victim.

**This attack assumes the browser's first request is plaintext HTTP.** See [[security/hsts#Scheme Defaulting and HTTPS-First]] for why that assumption no longer holds by default on modern browsers.

## Scheme Defaulting and HTTPS-First

The SSL-stripping premise (that typing `example.com` sends a plaintext `GET http://`) rests on **scheme defaulting**. A bare hostname has no scheme, so the browser prepends one. Historically that default was `http://` (the early web ran on plaintext port 80, and not every site supported TLS), which produced the vulnerable first hop.

Modern browsers flipped the default:

- **Chrome 90** (April 2021): typed navigations without a scheme default to `https://` in the omnibox, with no plaintext hop first.
- **Chrome 94** (September 2021): **HTTPS-First mode**. Chrome attempts HTTPS for *all* navigations (including `http://` links and old bookmarks), showing a full-screen warning before falling back to HTTP.
- **Chrome 115+** (2023): began enabling HTTPS-First by default for all users.
- **Firefox**: ships **HTTPS-Only Mode** (opt-in, per-profile).

So on a current browser the "plaintext first request on first visit" is increasingly *not* the default. The browser tries HTTPS first and only falls back to HTTP on failure (cert error, DNS/connection failure, or no HTTPS support). The first-visit SSL-stripping window narrows to fallback and legacy cases such as hardcoded `http://` links the page can't upgrade, old browsers, or an HTTPS attempt the browser abandons.

**HSTS preload is still stronger.** HTTPS-First is *best-effort with fallback*. If HTTPS fails, it downgrades to HTTP. A preloaded HSTS entry is *strict*. It hard-refuses HTTP entirely, with no fallback. Browser HTTPS-First narrows the attack surface; preload closes it.

## The HSTS Header Fields: Max-Age, includeSubDomains, Preload

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

- **`max-age`**: how long (in seconds) the browser remembers the rule. Recommended: 2 years (63072000s).
- **`includeSubDomains`**: applies HSTS to all subdomains.
- **`preload`**: opts into the browser preload list.

The header **must be served over HTTPS**. Browsers ignore it over HTTP (otherwise an attacker could forge it).

## TOFU Problem (Trust on First Use)

HSTS only protects after the browser has seen the header once. The very first visit is still vulnerable. The browser doesn't yet know to upgrade. This gap is the TOFU problem.

Other TOFU examples. SSH host fingerprints are trusted blindly on first connection.

## Preload

Adding `preload` and submitting the domain to the HSTS preload list solves TOFU. The list is **hardcoded into browser binaries** (Chrome, Firefox, Safari share one). The browser enforces HTTPS before ever visiting the site.

**Tradeoff:** preload is effectively permanent. Removal takes months (submit request → wait for processing → wait for browser releases → wait for user updates). Every subdomain must support HTTPS. Any subdomain without a valid TLS certificate becomes completely inaccessible (hard browser error, no workaround).

## Cross-Host Redirects

```
http://example.com → https://www.example.com    ← BROKEN
```

The HSTS header from `www.example.com` only protects `www.example.com`. The bare domain `example.com` never served HSTS over HTTPS, so `http://example.com` remains vulnerable on **every** visit. Not just the first.

**Fix. Redirect same-host first:**

```
http://example.com → https://example.com → https://www.example.com
```

The middle hop lets `example.com` serve its own HSTS header. This reduces the vulnerability to the TOFU problem (first visit only). Full protection still requires `preload`.

## Full Defense Stack

1. **Same-host HTTPS redirect**. Each domain serves its own HSTS header
2. **HSTS with `max-age` + `includeSubDomains`**. Protects returning visitors
3. **`preload`**. Protects first-time visitors

## What the HSTS Header Looks Like on a Real Site

The header is just a plain response header on an HTTPS response. No middleware magic at the protocol level. Inspecting a real site:

```bash
$ curl -sI https://github.com | grep -i strict-transport-security
strict-transport-security: max-age=31536000; includeSubdomains; preload
```

GitHub uses `max-age=31536000` (1 year), not the 2-year wiki recommendation. A deliberate tradeoff to limit blast radius if a subdomain ever needs to drop HTTPS.

**Setting it in Rails** (via `ActionDispatch::SSL` middleware):

```ruby
# config/environments/production.rb
config.force_ssl = true
config.ssl_options = {
  hsts: {
    expires: 1.year,
    subdomains: true,
    preload: true
  }
}
```

`force_ssl = true` does two things. Redirects HTTP→HTTPS **and** adds the `Strict-Transport-Security` header on HTTPS responses.

**Raw equivalent** (any framework):

```ruby
response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
```

The security does not come from the header itself. It comes from (a) browser persistence of the rule and (b) TLS authenticating the header's origin on the HTTPS response it arrived on.

## Browser Storage

Browsers maintain a persistent **HSTS store** per user profile. A local database of `(host, expiry, includeSubDomains)` tuples.

**On receiving the header** (over HTTPS only):
- Parse `max-age` + directives, stamp `received_at`, write or update the entry.
- Every subsequent HTTPS response refreshes `max-age`: a sliding window.
- `max-age=0` **deletes** the entry (the spec's opt-out mechanism).

**On every navigation, before DNS/TCP:**
1. Check the **static preload list** (baked into the browser binary, e.g. Chromium's `transport_security_state_static.json`). Hit → upgrade to HTTPS.
2. Else check the **dynamic store**. Match the host directly, or any parent with `includeSubDomains`. Hit and not expired → upgrade.
3. Otherwise fall through to normal resolution.

The "upgrade" rewrites `http://` to `https://` in-memory before any packet leaves the machine. DevTools shows it as an internal `307 Internal Redirect`. Zero network round trip, zero MitM opportunity.

**Where it lives on disk:**
- Chrome: `~/.config/google-chrome/<Profile>/TransportSecurity` (JSON)
- Firefox: `~/.mozilla/firefox/<profile>/SiteSecurityServiceState.txt`

Chrome also exposes `chrome://net-internals/#hsts` for inspecting, adding, or deleting entries in the dynamic store. Useful when debugging a site you accidentally pinned.
