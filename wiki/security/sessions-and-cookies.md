---
title: Sessions and Cookies
aliases:
- sessions vs cookies
- web sessions
- session id
- session cookie
tags:
- security
- web
- sessions
- cookies
created: '2026-11-12'
updated: '2026-11-12'
source_skill: study
flashcard_ids:
- cmne7xoxj002z0msoiuekt37c
- cmne7xoz0003d0mso56mopmir
- cmne7xp1a003z0msolwwfkqtm
- cmne7xp4r004t0mso8om67lfk
- cmne7xp80005j0msoxf0ahtrj
- cmne7xpbl006d0msopwlifvma
- cmne7xpd9006r0msob80gmzu2
- cmne7xpfk007b0mso3zv5ksk2
- cmw1ic5y400004x1aeq33jobr
- cmne7xpio00810msopmyj47b8
- cmne7xpkx008l0mso7o70oa9c
- cmne7xqa000ev0msoc3cxgj35
- cmne7xqbz00fd0msoo4ut2o0y
- cmne7xsjk00yj0msof6m4bs3k
- cmw1i9bfl0000w91a4wc8vrf2
- cmne7xslt00z30msoul4by4v8
- cmne7xso100zn0msoa7zhlft1
- cmne7xsui011d0mso90f5y7om
- cmne7xsvh011p0msonfjcxkol
- cmne7xszz012r0msomkmjmptu
- cmne7xt1n01350msoddyeyynj
- cmne7xt5v01450msotlupzovp
- cmne7xtac01550mso0so9c4um
- cmne7xtdc015z0msomwlu8l9d
- cmne7xtg0016n0msos4fpmiwp
- cmne7xtn5018h0msojp15dpo1
- cmw1t9ykc0000p61aeeuuurvb
- cmne7xtpy01990mso3crf10ii
- cmne7xtsa019x0msov9eewiq6
- cmne7xtxj01b70mso1jn6497o
- cmne7xuxo01jx0msoftnx2c68
- cmne7xv4001ld0msofpi1hvtq
- cmne7xvea01nx0msofu0xbhi0
- cmne7xvfv01ob0msotml57vug
- cmne7xwgy01xj0mso3pl7n1ls
- cmne7xxbf024v0msolzlfh20f
- cmne7y9va056d0mso5h5urtg6
- cmne7yedn06bz0mso8xj7vrk1
- cmne7yee906c50msov3oihw0y
- cmne7yef106cb0msof3uy8hik
- cmne7yegh06cn0msoe57ldd6e
- cmne7yel106dv0mso1y4hed9s
- cmw1ibc4500007m1alripur7a
- cmoa24zkv000fs70m16evouf9
- cmpic0zlp00077r0magx6rude
- cmw256ro500003x1afmafdqq5
- cmprdt5b10009b20mfk2o7ikg
- cmw257d7c00001c1aloo1zeet
- cmprdt7is000ab20m9wpait61
- cmqndsb0d0005vy0m3tt0dxe3
- cmscztkxc0002rz0me71kgeng
- cmsczygnl0000h60mlvh5uosg
- cmsczywkq0001h60muypyd01n
- cmsczyybr0002h60mzarbuf0a
- cmsczyznz0003h60m40o3q8hk
- cmw1i8pja0000my1acntkbf2w
- cmsczz0zt0004h60miu3bwcn7
- cmsczz8nn000ah60mv92jn82k
- cmsczzb9o000ch60m3bb9o9dh
- cmso9yhxg000ex90m1zha8a5n
- cmso9ykbq000fx90mszoruik6
- cmso9ym98000gx90mh7e0m70z
- cmso9yrl2000ix90mwzdcjppu
- cmw2em9js0001a01af56feyui
- cmtiqqdbr0006mn0mbeijiid4
- cmw25ozq4000dm81agvzu6y5k
- cmtiqqlfb0007mn0mly4dsb6r
- cmvj7fs6b00010f1aqwc45bhv
- cmvnkwfp10007g61ae9nj53eg
- cmw25vnut0013m81axxqhnxmn
- cmvno7tt80003cl1ai8exu6tt
- cmvw0ubwe0001va1a04no9hqr
- cmw1icjtt0000um1agj8a2qxr
- cmw1icmbs0001um1agewwubpf
- cmw1icotq0002um1axjrqrcg9
- cmw1t3v100000em1ayhiwep31
- cmw1t3vux0001em1aa1cizy2o
- cmw1t3ws10002em1atejzjlo2
- cmw1t6tfe0000up1awcjci49o
- cmw1t958k0000fv1admtileni
- cmw1t996n0001fv1asyng5d8i
- cmw1tbock0001xl1ah27jpanx
- cmw1tdjmz0000u61a8hc2k8ur
- cmw255g7v00020e1a4raahexz
- cmw2567em0000ix1apu7pce54
- cmw25688z0001ix1autah5gft
- cmw2569f20002ix1aiyo5m7n0
- cmw256a450003ix1agkt9t9uw
- cmw25v2kh0010m81a8jz9ezck
- cmw25v5970011m81ab1z4bn0p
- cmw4mx7cb0000x81a6lg7l681
- cmwd7t91e00003r1a17suzm25
- cmwd7tem700013r1aj3mvgkng
- cmwd845u000023r1a0sf8r4f5
- cmwd84ahi00033r1a8w53f9mv
---

# Sessions and Cookies

HTTP is stateless. The server treats every request as independent of the last one. A session adds a user's state on top of that and carries it from one request to the next. A cookie is a browser mechanism, and the usual way to tell the server which session a request belongs to. They are two different things.

## Two Roles

| | Cookie | Session |
| --- | --- | --- |
| What it is | A small value the browser stores and sends back | A record of one user's state, such as a user id or a cart |
| Where it lives | In the browser | Usually on the server |
| Its job | Identify the session | Hold the state |

A request after login looks like this.

```
Cookie: sid=a91f3c
```

The value `a91f3c` holds no name and no cart. The server uses it as a key, finds the session record, and the record points to the user. The cookie identifies the session. The session carries the state.

## Why the Cookie Carries an Opaque Id

An app that trusts a plain cookie such as `user_id=42` lets any user edit it to `user_id=7` in the browser's dev tools and act as that user. Two designs close the hole.

- **Random id with a server-side record**. The server accepts only ids it issued, so a guessed or edited id matches nothing. OWASP asks for a random, meaningless id with at least 64 bits of entropy, and says the meaning of the session belongs on the server.
- **Signed cookie**. The server adds an HMAC of the payload. An edited payload no longer matches the tag, and nobody can forge a new tag without the key. A Rails message verifier joins the base64 payload and the digest with `--`. The payload is only encoded, so anyone can decode and read it. The signature gives integrity, not secrecy.

## Where the State Lives

**Server-side store.** The cookie holds only the key. The server ends a session by deleting its record. Every app node needs the same store, because an opaque id means nothing without its record.

**Cookie store.** Rails `CookieStore` keeps all session data in the client's cookie. Current Rails encrypts it, which gives integrity and confidentiality, and a cookie is limited to 4 kB. The design has consequences.

- The server keeps no per-session record, so it cannot revoke one stolen session.
- A user can replay an old cookie. If the balance of a credit lives in the session, the user saves the cookie, spends the credit and sends the old copy back. The fix is to keep the balance in the database and only the user id in the session.
- A valid signature proves the server wrote the cookie, not that it is still current. The Rails guide puts it this way. Session cookies do not invalidate themselves and can be reused.
- Changing `secret_key_base` expires every active session, so everyone has to log in again.

Rails can rotate the digest and the cipher used for cookies, so old cookies stay readable while they are rewritten. The Rails guide documents that for digests and ciphers. It does not document secret or serializer rotation.

## Lifetime and Logout

- A cookie without `Expires` or `Max-Age` is a session cookie. It lasts until the browser session ends. Session restore can bring it back as if the browser never closed. When both attributes are set, `Max-Age` wins.
- A client can edit its own cookie, so expiry must be enforced on the server. OWASP gives idle timeouts of 2 to 5 minutes for high-value apps and 15 to 30 minutes for low-risk ones, and absolute timeouts of 4 to 8 hours.
- Logout must invalidate the session on the server. Deleting the cookie in the browser does not stop a copied token from working.
- Shared terminals need a prominent logout button, because users who close the tab leave a valid session behind.
- A single sign-on login has a second session at the identity provider. See [[security/identity-providers]].

## Attacks on the Session Id

**Session fixation.** The attacker plants a known id, the victim logs in under it, and the attacker now holds an authenticated session. OWASP and Rails name these ways to plant the id.

- A link that carries the id in the URL, if the app accepts ids from the query string
- Script on a pre-login page that writes the id into `document.cookie`
- HTTP response splitting that injects a `Set-Cookie` header
- A cookie set from a sibling subdomain with a broad `Domain` attribute

The attacker keeps the planted session alive by using it regularly. The fix is a new session id at login and a destroyed old one. In Rails that is `reset_session`, which drops the session values, so carry over what you need. OWASP asks for a new id after any privilege change, for example when a user becomes an admin.

**Hijacking.** An attacker who gets the cookie can act as the user. The cookie leaks through script injection (see [[security/xss]]) or through sniffing on plain HTTP. Binding a session to the client's IP address or user agent helps detect theft. OWASP says these properties cannot be trusted as a defense, and the Rails guide warns that they change during a session, which can lock out real users.

## Cookie Attributes

| Attribute | What it does | Notes |
| --- | --- | --- |
| `HttpOnly` | Hides the cookie from `document.cookie` | Script requests still carry it, so it stops theft, not use |
| `Secure` | Sends the cookie over HTTPS only | http: sites cannot set it. `localhost` is exempt, and Safari does not support that exception |
| `SameSite` | `Strict` sends it only on same-site requests. `Lax` adds top-level GET navigations. `None` sends it everywhere | `None` requires `Secure`. Explicit `Lax` withholds the cookie on cross-site POST, `fetch`, subresource and iframe requests |
| `Domain` | Omitted, the cookie goes only to the exact host. Set, it includes all subdomains | OWASP advises leaving it unset |
| `Path` | Limits the cookie to matching URLs | Not a security boundary |
| `Max-Age`, `Expires` | Lifetime in seconds, or an HTTP date | `Max-Age` wins |
| `__Secure-` prefix | Cookie needs `Secure` and an HTTPS page | |
| `__Host-` prefix | Also needs `Path=/` and no `Domain` | OWASP recommends it for session ids |
| `Partitioned` | Keys the cookie by the top-level site, so an embed gets a separate jar per site | Needs `Secure` |

OWASP's example for a session cookie sets most of these at once.

```
Set-Cookie: __Host-SessionID=<value>; Secure; HttpOnly; SameSite=Strict; Path=/
```

Same-site means the same scheme and the same registrable domain. `app.example.com` and `api.example.com` are same-site, so `SameSite=Lax` does not block a cookie between them. A request from `http://example.com` to `https://example.com` is cross-site. `SameSite` is defense in depth. It does not replace a CSRF token.

## Cookies and CSRF

The browser attaches a cookie to every matching request, whichever site triggered it. A request that carries a session cookie therefore needs a CSRF defense. See [[security/csrf]] for tokens and `SameSite`, and [[security/identity-providers]] for how Bearer tokens differ.

## Open Questions

- What browsers do with a cookie that has no `SameSite` attribute is not settled in the sources checked. Chromium treats it as `Lax`, with a two-minute allowance for POST requests. MDN says only that some browsers do, and Firefox and Safari are unclear. Set the attribute explicitly.
- MDN (June 2026) says Chrome does not block third-party cookies by default. Firefox enables Total Cookie Protection by default.
- The cookie rules above come from an IETF Internet-Draft that updates RFC 6265, so treat the details of default `Lax` behavior as browser behavior, not settled standard.

## Related Concepts

- [[security/csrf]]: why automatic cookie attachment makes forged cross-site requests possible
- [[security/xss]]: how injected script steals or uses the session cookie
- [[security/same-origin-policy]]: the browser rule that stops other sites from reading your cookies
- [[security/identity-providers]]: identity-provider sessions and Bearer tokens
- [[security/hsts]]: transport hardening that keeps cookies off plain HTTP
- [[security/content-security-policy]]: nonces, and why a nonce taken from the session id repeats for the whole session
- [[security/key-derivation-and-domain-separation]]: how Rails derives separate keys for signed and encrypted cookies from one secret

## References

- [MDN: Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie): attribute semantics, defaults and prefixes
- [MDN: Using HTTP cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Cookies): session cookies, session restore, localhost exception
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html): id properties, renewal, expiry, logout
- [Rails Security Guide](https://guides.rubyonrails.org/security.html): `CookieStore`, replay, `reset_session`, rotation
- [IETF cookie draft](https://httpwg.org/http-extensions/draft-ietf-httpbis-rfc6265bis.html): host-only cookies, `SameSite` grammar, prefixes
- [Chrome CHIPS](https://privacysandbox.google.com/3pcd/chips): partitioned cookies
