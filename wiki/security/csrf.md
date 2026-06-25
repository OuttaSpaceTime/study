---
title: CSRF
aliases:
- csrf
- cross-site request forgery
- xsrf
tags:
- security
- web
created: '2026-05-07'
updated: '2026-05-07'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- Why the browser makes CSRF possible
- Three preconditions for a successful CSRF attack
- Why SameSite=Lax doesn't fully protect against subdomain attacks
- Synchronizer token vs. signed double-submit cookie
- Why CSRF tokens don't stop XSS
- Login CSRF and the pre-session token fix
last_probed:
- Login CSRF and the pre-session token fix
- Why the browser makes CSRF possible
- Three preconditions for a successful CSRF attack
- Why SameSite=Lax doesn't fully protect against subdomain attacks
- Synchronizer token vs. signed double-submit cookie
- Why CSRF tokens don't stop XSS
review_interval: 18
next_review: '2026-07-13'
---

# CSRF (Cross-Site Request Forgery)

An attacker tricks the victim's browser into sending a state-changing request to a trusted site. The site can't tell the request came from `evil.com` rather than its own UI.

## Why the browser makes CSRF possible

The browser attaches cookies to every request targeting a domain, regardless of which page triggered the request. A form on `evil.com` that posts to `bank.com/transfer` will carry the victim's `bank.com` session cookie. The server sees a valid session and treats the request as legitimate.

**Modern default:** Since ~2020, browsers default to `SameSite=Lax`, which blocks cross-site cookies on subresource requests (forms, `fetch`, `img`). POST, PUT, and DELETE are always blocked cross-site under Lax. In practice this stops most naive CSRF. It is not a complete fix though. Top-level GET navigations still send the cookie (leaving state-changing GET endpoints exposed), and requests from a same-site subdomain (`evil.example.com → app.example.com`) are not blocked at all. Same-site is not the same as same-origin.

## Three preconditions for a successful CSRF attack

All three must hold. Remove any one and CSRF is blocked:

1. The app uses cookies for authentication
2. The request changes state (transfer funds, change email, delete account)
3. The request parameters are attacker-predictable (no secret the attacker can't know)

## Why SameSite=Lax doesn't fully protect against subdomain attacks

SameSite=Lax (browser default since ~2020) blocks cross-site cookies on subresource requests (forms, `fetch`, `img`). It still sends cookies on **top-level GET navigations**, so any state-changing GET endpoint is unprotected.

More critically, SameSite is scoped to **eTLD+1** (registrable domain), not the full origin. `app.example.com` and `evil.example.com` share the same eTLD+1 (`example.com`), so they are **same-site**. SameSite=Strict still sends the cookie on requests from `evil.example.com` to `app.example.com`.

SameSite is defense-in-depth, not a primary defense. A compromised subdomain bypasses it entirely.

## Synchronizer token vs. signed double-submit cookie

**Synchronizer token (stateful):** the server generates a secret per session, stores it server-side, and renders it into every form as a hidden field. On submit the server checks it matches. The attacker can't read the hidden field due to SOP.

**Double-submit cookie (stateless):** the server sets a random value as a cookie (not `HttpOnly`; JS must read it), and the frontend includes the same value in the request body or header. The server checks cookie == body value. No server-side session storage needed.

The naive version is broken. An attacker with a compromised sibling subdomain can write a cookie scoped to the parent domain (`document.cookie = "csrf=known; domain=.example.com"`), then forge a matching body value. The fix is a **signed token**. The form field value is `HMAC(sessionID + randomValue, serverSecret)`. The attacker can't forge the HMAC without the server secret.

> [Note] The CSRF cookie must NOT be `HttpOnly`. The session cookie SHOULD be `HttpOnly`. These are different cookies serving different roles.

## Why CSRF tokens don't stop XSS

CSRF tokens rely on SOP to prevent cross-origin reads. XSS gives the attacker same-origin code execution. SOP no longer applies. The attacker's injected script can read the hidden token directly from the DOM or from the cookie, then forge a fully valid request.

**XSS defeats any CSRF mitigation.** Fix XSS first. CSRF tokens and XSS defenses are orthogonal controls. You need both.

## Login CSRF and the pre-session token fix

Standard CSRF tokens are tied to an authenticated session. The login form has no session yet, so there's no token to validate.

**Login CSRF attack:** the attacker forges `POST /login` with their own credentials. The victim ends up logged into the attacker's account and may enter sensitive data (address, payment info) the attacker can then retrieve.

**Fix:** issue a **pre-session CSRF token** on the login page. It is stored in a temporary (unauthenticated) session and validated when the login form is submitted.

## Related Concepts

- [[security/same-origin-policy]]: SOP is what makes CSRF tokens work. It blocks cross-origin reads of the hidden token value.
- [[security/hsts]]: transport-layer hardening; a sibling concern to CSRF

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html): canonical defense taxonomy; synchronizer token, double-submit, Fetch Metadata, SameSite details
- [MDN: Cross-site request forgery (CSRF)](https://developer.mozilla.org/en-US/docs/Web/Security/Attacks/CSRF): browser-model perspective; cross-origin vs. cross-site distinction
- [MDN: SameSite cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite): exact semantics of Strict/Lax/None and default-Lax behavior
