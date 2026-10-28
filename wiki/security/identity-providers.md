---
title: Identity Providers
aliases:
- idp
- identity provider
- oauth and openid connect login
- id token vs access token
tags:
- security
- web
- auth
- oauth
- oidc
- jwt
created: '2026-10-25'
updated: '2026-10-25'
source_skill: study-walkthrough
flashcard_ids:
- cmvnk1noi0000g61a2j2mnc23
- cmvnk1p3a0001g61asigcy619
- cmvnk1qhw0002g61apwoedjm1
- cmvnkv43g0005g61az1607lwt
- cmvnkv5on0006g61alh67bw83
- cmvnkwfp10007g61ae9nj53eg
- cmso9yoit000hx90mksjgn6nl
- cmsabsyne0009680mecz7zq22
- cmne7xzxj02rv0msoelt9emqc
- cmne7xzx902rt0mso4dku4tk9
explorables:
- https://claude.ai/artifact/7t2SJ2yyQZZb6sYLbSADFa
---

# Identity Providers

An identity provider (IdP) logs users in and vouches for them to other systems with signed tokens. Auth0, Microsoft Entra ID and Siemens ID (built on Auth0) are IdPs. Your app never sees the password. It trusts what the IdP signs.

## TL;DR

- **Three logins, not one.** Your app's session cookie, Auth0's session cookie and Microsoft's session cookie live on three domains with three expiries.
- **Tokens travel server to server.** In the authorization code flow the browser only carries a short-lived code. The tokens come back in a response body to whoever redeems the code.
- **Federation re-issues.** When Auth0 brokers to Microsoft, Microsoft's tokens stop at Auth0. Your backend only ever sees tokens Auth0 signed.
- **ID token for the app, access token for the API.** An API accepts only tokens whose `aud` names it.
- **Trust comes from the signature plus your config.** The IdP holds the private key. Your backend checks the signature with the IdP's public keys, for the one issuer it was configured to trust.
- **Silent checks need the IdP's cookie.** A hidden iframe can't see it where third-party cookies are blocked. A whole-page redirect can.

## Roles

| Role | OAuth / OIDC name | In this setup |
|---|---|---|
| Logs the user in, issues tokens | Authorization server / OpenID Provider | Auth0 (brokering to Microsoft) |
| Asks for the login, receives tokens | Client / Relying Party | your backend, the other page |
| Accepts access tokens | Resource server | your API |

OAuth 2.0 is delegated authorization. It gets a client a token to call an API. OpenID Connect (OIDC) adds authentication on top, in the form of the ID token, a JWT about the login itself.

## Three Session Layers

Auth0 names them the application session, the Auth0 session and the identity provider session. Each is a cookie on its own domain:

| Layer | Cookie lives on | Typical lifetime |
|---|---|---|
| Your app | `app.example.com` | you decide (e.g. 8 hours) |
| Auth0 | `your-tenant.auth0.com` | idle and absolute timeout per tenant (self-service max 3 days idle, 30 days absolute) |
| Microsoft | `login.microsoftonline.com` | Entra default: rolling 90 days |

Clicking Login with an expired app cookie but a live Auth0 session shows no form. Auth0 finds its own cookie and redirects straight back, a quick flicker. With the Auth0 session gone but Microsoft's alive, Auth0 shows its connection page and Microsoft signs in without a password. Only with all three gone does the user type a password.

Auth0's idle timer only resets when the browser visits Auth0. While the Auth0 session lives, Auth0 never goes back to Microsoft, so Entra's sign-in frequency does not apply.

## The Login Round Trip

The authorization code flow, with Auth0 federating to Microsoft:

1. `GET /login` on your backend. It redirects to Auth0's `/authorize` with `state`, `nonce` and a PKCE `code_challenge`, and sets the same `state` in a short-lived cookie.
2. Auth0 redirects onward to Microsoft. Toward Microsoft, Auth0 is the client, with its own app registration, callback and state.
3. Microsoft signs the user in and redirects to Auth0's `/login/callback` with a code meant for Auth0.
4. Auth0 redeems that code server to server. Microsoft's tokens are addressed to Auth0 and stop there.
5. Auth0 sets its own session cookie and redirects to your `/callback?code=…&state=…`.
6. Your backend compares `state` with its cookie, then redeems the code at `POST /oauth/token` with its client secret and `code_verifier`.
7. Auth0 answers with an ID token and an access token in the JSON body, both signed by Auth0 with `iss: https://your-tenant.auth0.com/`.
8. Your backend answers the callback with `Set-Cookie: session=…; HttpOnly; Secure; SameSite=Lax`. The tokens stay on the server.

The state cookie must be `SameSite=Lax`, not `Strict`. The callback is a top-level navigation arriving from Auth0, and a `Strict` cookie would be missing, so every login would fail the check.

## state and PKCE

Both protect the code in the redirect, from different sides:

- **`state`** answers whether this browser started this login. It stops **login CSRF**: an attacker feeds your callback a code from the attacker's own unfinished login, and the victim ends up logged into the attacker's account. The attacker controls the URL but cannot set a cookie for your domain, so the comparison fails.
- **PKCE** answers whether whoever redeems the code is whoever asked for it. The client keeps a random `code_verifier` and sends only its hash (`code_challenge`). The token request must present the original. A stolen code is useless without it.

Browser apps cannot keep a client secret, so PKCE is mandatory for them. For a backend with a secret it is still recommended, because it also stops code injection. Auto-login with `prompt=none` is an ordinary authorization request with the same checks, so it does not open a login-CSRF hole by itself.

## ID Token vs Access Token

| | ID token | Access token |
|---|---|---|
| Addressed to (`aud`) | the app that logged in | the API it will call |
| Read by | that app | that API only. Clients treat it as opaque |
| Used for | knowing who logged in, starting a session | `Authorization: Bearer` on API calls |

An app that calls your API with Auth0's SPA SDK reads the user from the ID token (`getUser()`) and sends the access token (`getTokenSilently()`). It must request `audience: "https://api.example.com"`. Without an audience, Auth0 issues an access token that only works for its own `/userinfo`.

> [Warning] Never accept an ID token as an API credential. It is genuinely signed by the same issuer, so only the `aud` check stops it.

## How a Backend Trusts a JWT

A JWT is three base64url parts: header, payload, signature. It is signed, not encrypted, and anyone can write one with any claims. Trust rests on two things:

1. **Your configuration.** The issuer URL is a decision you made once. Nothing inside a token can change it.
2. **The signature.** Only the IdP holds the private key. It publishes the public keys at `https://your-tenant.auth0.com/.well-known/jwks.json`, which can verify a signature but not create one. A valid signature proves the IdP made the token and no character changed.

The checks, all of which must pass:

| Check | Stops |
|---|---|
| Signature verifies with the issuer's JWKS key named by `kid` | edited payloads, tokens from other issuers |
| `iss` equals the configured issuer | tokens from another tenant |
| `aud` contains your API identifier | ID tokens, tokens for another API |
| `exp` in the future | expired tokens |
| `alg` on an allowlist (e.g. RS256), never `none` | `alg: none` and algorithm confusion |

```js
// express-oauth2-jwt-bearer runs all of these
app.use("/orders", auth({
  issuerBaseURL: "https://your-tenant.auth0.com/",
  audience: "https://api.example.com",
}));
```

Validation is local, with cached public keys. That makes it fast, but a validly signed token is accepted until `exp`, even after the user logs out.

A backend with two ways in defends each one differently. The session cookie is attached by the browser automatically, so it needs CSRF defenses. A Bearer token is never attached automatically, so CSRF does not apply, but a leaked token works for anyone until it expires.

## Silent Login and Third-Party Cookies

Skipping the Login click means asking Auth0 whether a session exists without showing a screen (`prompt=none`). The answer depends on whether the browser sends Auth0's cookie:

| Method | Chrome | Safari, Brave | Firefox |
|---|---|---|---|
| Your backend asks Auth0 | impossible. The cookie is in the browser | same | same |
| Hidden iframe, `prompt=none` | works (third-party cookies on by default) | `login_required`. Cookie blocked | `login_required`. Cookie partitioned |
| Hidden iframe on a custom domain (`login.example.com`) | works | works | works |
| Whole-page redirect, `prompt=none` | works, visible flicker | works | works |

Inside your page, Auth0 is a third-party site. The login page's framing block is not the reason. `prompt=none` never renders a page.

## Auto-Login and Logout Depth

Auto-login on page load is safe only together with a logout that clears enough layers:

| Logout clears | Without auto-login | With auto-login |
|---|---|---|
| your app only | next person clicks Login and is in the previous user's account | the user can never stay logged out, and the next person is in with zero clicks |
| app + Auth0 (`/oidc/logout`) | next person reaches Microsoft, which still offers the previous account | same, after a `login_required` round trip |
| app + Auth0 + Microsoft (`federated`) | clean | clean |

Federated logout also signs the user out of every other Microsoft app in that browser, which is why Auth0 calls it not recommended outside shared machines. The safer default is clearing the Auth0 layer on logout, or skipping auto-login after an explicit logout.

## Tradeoffs & Gotchas

- **Entra token versions.** v2 access tokens carry the API's client ID GUID as `aud`, not the `api://` URI. Entra access tokens use `typ: JWT`, so a strict RFC 9068 `at+jwt` check rejects them. Tokens for Microsoft Graph cannot be validated by your API at all.
- **Federation.** Your API trusts its direct issuer only. With Siemens ID or Entra behind Auth0, it never validates their tokens.
- **Backend-for-frontend is the recommended pattern.** RFC 10017 ranks a backend that holds the tokens and gives the browser only a cookie as the most secure option for browser apps. Your own frontend already works this way. Consensus among practitioners (Duende, Curity, De Ryck).
- **Keeping tokens in memory instead of localStorage is harm reduction, not a fix.** Under XSS, an attacker can run a fresh login flow and get new tokens wherever they are stored. Consensus, confirmed by RFC 10017.
- **"An ID token is fine for a first-party API."** An older Auth0 blog post allows it. Current Auth0 and Entra docs say never. Treat it as outdated.

## Related Concepts

- [[security/csrf]]: why the state check exists, and why cookie-authenticated endpoints need CSRF defenses while Bearer endpoints do not
- [[security/same-origin-policy]]: why `evil.com` cannot set or read your cookies
- [[security/xss]]: why no browser token storage survives script injection

## References

- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html): ID token claims, `nonce`, `prompt=none` and its errors
- [RFC 9700, OAuth 2.0 Security BCP](https://www.rfc-editor.org/rfc/rfc9700.html): PKCE, CSRF protection, no implicit flow
- [Auth0 session layers](https://auth0.com/docs/manage-users/sessions/session-layers): the three layers and how each logs out
- [Microsoft Entra access tokens](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens): validation steps, `aud`, key discovery

**Practitioner / opinion:**

- [Auth0 blog, ID token vs access token](https://auth0.com/blog/id-token-access-token-what-is-the-difference/): the most common mistake, ID tokens sent to APIs
- [Duende, the BFF pattern](https://duendesoftware.com/blog/20210326-bff): why third-party cookie blocking pushed tokens out of the browser
