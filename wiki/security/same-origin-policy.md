---
title: Same-Origin Policy
aliases:
- SOP
- same origin policy
tags:
- security
- web
- browser
created: '2026-04-29'
updated: '2026-04-29'
source_skill: study-walkthrough
depth: 1
probe_sections:
- What an Origin Is
- What SOP Actually Blocks
- The Threat Model
- SOP Is Not Configurable
- Server-to-Server Requests
last_probed:
- What an Origin Is
- What SOP Actually Blocks
- The Threat Model
- SOP Is Not Configurable
- Server-to-Server Requests
---

# Same-Origin Policy

## TL;DR

- An **origin** is `scheme + host + port`. All three must match.
- SOP is a **browser-enforced** rule that blocks JavaScript from **reading** cross-origin responses. It does not block the browser from **loading** cross-origin resources.
- The threat it stops: a malicious page using the user's ambient session cookies to read data from another site they are logged into.
- SOP is always on. There is no off switch. Servers opt **in** to relaxation via CORS headers (`Access-Control-Allow-Origin`, etc.).
- Server-to-server requests have no concept of SOP: there is no browser, no ambient credentials, nothing to enforce.

## What an Origin Is

Origin is the tuple `(scheme, host, port)`. Two URLs share an origin only when all three match. See [[networking/url-anatomy]] for what each component means.

| URL A | URL B | Same origin? | Why |
|---|---|---|---|
| `https://app.example.com` | `https://app.example.com/api` | yes | path is irrelevant |
| `https://app.example.com` | `http://app.example.com` | no | scheme differs |
| `https://app.example.com` | `https://api.example.com` | no | host differs |
| `https://app.example.com` | `https://app.example.com:8080` | no | port differs |

Subdomains are **different origins**. `app.example.com` and `api.example.com` cannot read each other's responses by default.

## What SOP Actually Blocks

The critical distinction is **loading vs. reading**.

- **Loading** a cross-origin resource is allowed. The browser fetches and uses it (executes a script, renders an image, applies a stylesheet, displays an iframe). Your JS never gets to inspect the raw bytes: there is no API to read what was loaded: so there is nothing to protect.
- **Reading** a cross-origin response from JS is blocked. `fetch()`, `XMLHttpRequest`, reading pixels from a tainted `<canvas>`, accessing the DOM of a cross-origin iframe: all blocked.

```html
<!-- allowed: browser loads and runs jQuery -->
<script src="https://cdn.jquery.com/jquery.min.js"></script>

<!-- allowed: browser renders the image -->
<img src="https://other.example.com/photo.jpg">
```

```js
// blocked: JS tries to read the response body
fetch("https://other.example.com/api/data")
  .then(r => r.text())  // SOP blocks this read

// blocked: canvas is "tainted" once a cross-origin image is drawn
ctx.drawImage(crossOriginImg, 0, 0)
ctx.getImageData(0, 0, w, h)  // throws SecurityError
```

The image renders visually, but JS cannot extract its pixels. Visual leak yes, programmatic read no.

## The Threat Model

SOP exists because browsers attach **ambient credentials** (cookies, HTTP auth, client certs) to outbound requests by **host**, not by **origin of the calling page**.

Without SOP:

1. User logs into `bank.com`. Browser stores a session cookie for `bank.com`.
2. User visits `evil.com`.
3. JS on `evil.com` runs `fetch("https://bank.com/account-balance").then(r => r.text())`.
4. Browser attaches the user's `bank.com` cookie automatically. The request is fully authenticated.
5. `bank.com` returns the user's real balance.
6. `evil.com`'s JS reads the response and exfiltrates it.

SOP cuts step 6. The response reaches the browser, but the browser refuses to hand the body to `evil.com`'s JS.

> [Note] SOP does not stop the request being **sent**. It stops the response from being **read**. Side effects (like a state-changing POST) can still happen: that is what CSRF tokens defend against, not SOP.

## SOP Is Not Configurable

There is no server header, browser flag, or runtime API that disables SOP for production users. It is the default lock baked into every browser.

What you **can** configure is CORS (Cross-Origin Resource Sharing): the opt-in relaxation. The server adds:

```
Access-Control-Allow-Origin: https://trusted-app.com
```

The browser reads this header and, for that specific origin, allows the JS read that SOP would otherwise block. CORS is the key the server hands out; SOP is the lock the browser refuses to remove.

A common confusion. Developers say "I'll disable SOP on my server." That sentence is meaningless. SOP is not on the server. The server can only **opt origins in** via CORS, never **opt SOP out**.

## Server-to-Server Requests

SOP only exists in browsers. A Node.js, Ruby, or Go process calling `https://bank.com/api` runs no SOP check, because:

- There is no browser in the loop.
- There is no ambient user session: the server uses its own explicitly-attached credentials (API key, service token).
- There is no cross-origin JS context to protect.

This is also why the threat model is narrow. SOP defends against **a browser page abusing the user's session**. Server-side abuse is a different problem (API authentication, rate limiting, IP allowlists), not an SOP concern.

## Related Concepts

- [[security/hsts]]: forces HTTPS, eliminating the `http`/`https` scheme-mismatch downgrade path
- CORS: the opt-in mechanism servers use to relax SOP for specific origins (not yet a wiki page)
- CSRF: defends against cross-origin **state-changing requests**; SOP only restricts reads (not yet a wiki page)
