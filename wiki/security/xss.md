---
title: XSS
aliases:
- cross-site scripting
- DOM-based XSS
- Trusted Types
tags:
- security
- web
- browser
created: '2026-10-20'
updated: '2026-10-23'
source_skill: study-walkthrough
flashcard_ids:
- cmvh4hkad0000jq1aro023kh5
- cmvh4hlma0001jq1a5kb6oecs
- cmvh4hmro0002jq1aih2gg344
- cmvh4ho0w0003jq1a3jwnstmy
- cmowkcmwt0006rb0m3v0pbih8
- cmne7xxvt029t0msogj8pet75
- cmne7xxu2029f0msowdgy7bej
- cmne7y02502sx0msoqv2zedir
---

# XSS (Cross-Site Scripting)

An attacker gets their own script to run inside your page. It runs with your origin, so it can read the DOM, call your API with the user's cookies, and send anything it finds elsewhere. Same-origin policy does not help, because the script is not cross-origin. It is yours as far as the browser can tell.

## TL;DR

- **The slot decides what is dangerous.** Escaping stops a value from breaking out of its slot. It does nothing when the slot itself runs the value, as `href="javascript:..."` does.
- **Escape for the parser that reads the slot.** HTML entities mean something to the HTML parser only. Inside `<script>` they are garbage, and the JS parser needs JS escaping.
- **The safest slot is a data slot.** Put values in HTML text or a `data-` attribute and let JS read them, instead of writing them into code.
- **DOM-based XSS never touches the server.** When browser code moves a URL fragment into `innerHTML`, server-side escaping gets no turn. Fix the sink (`textContent`).
- **To render user HTML, sanitize with an allowlist.** Keep the few tags you want and drop the rest.
- **Enforce at the sink.** Trusted Types makes `innerHTML` and friends reject plain strings, so a forgotten sanitize call fails loudly.

## The Slot Decides What Is Dangerous

Escaping turns the characters `<`, `>`, `"`, `'` and `&` into entities. That stops the classic break-out:

```html
<!-- value: "><script>alert(1)</script> -->
<a href=""><script>alert(1)</script>">        <!-- unescaped: new tag -->
<a href="&quot;&gt;&lt;script&gt;...">          <!-- escaped: stays text -->
```

The `"` closes the attribute and the `>` closes the tag. Escaped, they cannot, and the value stays inside `href`.

A value that does not need to leave its slot is untouched by escaping:

```jsx
// React escapes this, and it still runs script on click
<a href={user.website}>{user.name}</a>
// user.website = "javascript:alert(1)"
```

`javascript:alert(1)` contains none of the escaped characters. The browser treats an `href` as a URL to follow, and a `javascript:` URL is code. So escaping only protects a value when its slot treats the value as inert text.

The fix for URL slots is to validate the scheme. Allow `https:` (and `http:` or `mailto:` if needed) and reject everything else. React 19 treats `javascript:` URLs in `href` and `src` as an error, where 16.9 to 18 only warned. [OWASP still calls URL validation the app's job](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html), since other frameworks and older React versions do not block it.

## Escape for the Parser That Reads the Slot

Rails' `<%= %>` HTML-escapes every value. Put that value inside a script block and the wrong parser reads it:

```erb
<%# bad: unquoted, the value becomes code %>
<script>var page = <%= params[:page] %>;</script>
<%# ?page=1;alert(document.domain) renders as var page = 1;alert(document.domain); %>

<%# still bad: quoted, HTML-escaped, read by the JS parser %>
<script>var q = '<%= params[:q] %>';</script>
<%# ?q=O'Brien renders as var q = 'O&#39;Brien'; %>
```

In the quoted version the attack `';alert(1);'` is blocked, but only by accident. The escaper wrote `&#39;` for the HTML parser, and the JS parser never decodes entities. So `q` holds `O&#39;Brien`, and real data is corrupted. Matching the encoder to the slot is the rule.

| Slot | What to do |
| --- | --- |
| HTML text, `<p>{x}</p>` | HTML-entity encode `& < > " '` |
| Attribute value | Attribute encode, and always quote the attribute |
| URL in `href` / `src` | Validate the scheme, URL-encode, then attribute encode |
| Quoted JS string | JS-escape (`\xHH`), never HTML-escape |
| CSS property value | CSS-encode, and only in a property value |

Some slots cannot be made safe by any encoding. Never put untrusted data directly inside `<script>` or `<style>`, in HTML comments, in tag or attribute names, in event-handler attributes like `onclick`, or in strings passed to `eval`, `setTimeout` or `setInterval`. Entity-encoding an `onclick` value fails because the HTML parser decodes the entities before the JS parser runs the handler.

### Keep Data Out of Code

The safest move avoids the JS slot entirely. Put the value where the HTML escaper is the right tool, and read it from JS:

```erb
<%# good: HTML attribute, HTML-escaped, decoded by the HTML parser %>
<div id="pager" data-page="<%= params[:page] %>"></div>
<script>
  const page = document.getElementById("pager").dataset.page;
</script>
```

Rails renders `data-page="O&#39;Brien"`, the HTML parser decodes it, and `dataset.page` is `O'Brien`. The encoder and the parser match, so the data arrives intact and can never become code.

## DOM-Based XSS

Here the server never sees the attack. Browser code reads an attacker-controlled **source** and writes it into a dangerous **sink**:

```js
// bad
const name = new URLSearchParams(location.search).get("name");
document.getElementById("greeting").innerHTML = "Hello " + name;
// ?name=<img src=x onerror=alert(document.domain)>
```

Every server template can be escaped perfectly and this page is still exploitable. The attacker writes the URL and mails it to the victim, and the string travels from `location.search` to `innerHTML` without passing through Rails at all.

Common sources are `location.search`, `location.hash`, `document.referrer`, `postMessage` data, `localStorage`, and API responses. Dangerous sinks:

- **HTML parsing**: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`
- **Code execution**: `eval`, `new Function`, `setTimeout` / `setInterval` with a string
- **URL navigation**: assigning `location`, `href` or `src` from untrusted input (`javascript:` again)

The fix is to change the sink rather than remember to escape the data:

```js
// good: textContent never parses HTML
document.getElementById("greeting").textContent = "Hello " + name;
```

`textContent` shows `<img ...>` as literal characters. `innerText` is also safe but CSS-aware and slower. Escaping before `innerHTML` works too, but every future `innerHTML` line then depends on someone remembering it.

## Rendering User HTML with a Sanitizer

Comments with bold text and links need real HTML, so neither `textContent` nor escaping fits. Escaping `<b>hi</b>` shows the tags literally. The string has to go through `innerHTML`, and something must decide which parts survive.

There are two ways to write that decision:

- **Blocklist**: remove everything that can run JS. HTML has dozens of handlers, `javascript:` URLs, SVG and MathML tricks, and browsers add more. One missing entry is a vulnerability.
- **Allowlist**: keep only `<b>`, `<i>`, `<a href>` with `https:`, and drop everything else. One missing entry means some formatting does not render, and someone files a ticket.

An HTML sanitizer parses the HTML and applies an allowlist. Use [DOMPurify](https://github.com/cure53/DOMPurify) in the browser and `sanitize` in Rails (built on rails-html-sanitizer). Never modify the sanitized output before inserting it, because concatenation or string replacement can rebuild a payload. Keep the sanitizer patched, since new bypasses keep appearing.

## Enforcing It at the Sink with Trusted Types

With 200 `innerHTML` calls and new ones every week, "always sanitize" is a rule someone will forget. Sanitizing on input does not close the gap either. DOM-based sources never pass through your input layer, and the input layer does not know which slot a value will land in.

Every string headed for the screen passes through a sink, and the browser implements the sinks. [Trusted Types](https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API) moves the check there:

```js
const policy = trustedTypes.createPolicy("sanitize", {
  createHTML: (input) => DOMPurify.sanitize(input),
});

el.innerHTML = policy.createHTML(comment); // ok: a TrustedHTML object
el.innerHTML = location.search;            // TypeError: plain string
```

```
Content-Security-Policy: require-trusted-types-for 'script'; trusted-types sanitize
```

- `require-trusted-types-for 'script'` makes injection sinks reject plain strings with a `TypeError`.
- `trusted-types <names>` limits which policy names `createPolicy` may register.
- `TrustedHTML`, `TrustedScript` and `TrustedScriptURL` are the three types, matching HTML, script and script-URL sinks.
- A policy named `default` intercepts plain strings instead of throwing. It is meant for migrating an existing codebase.

The browser does no sanitizing itself. It does not know your allowlist. You supply the transformation, and the browser enforces that it ran. A forgotten sanitize call now breaks the feature in development instead of shipping as a silent hole. Trusted Types has been Baseline across major browsers since February 2026, so older articles calling it "Chromium-only" are out of date.

## Tradeoffs & Gotchas

- **Framework escape hatches**: auto-escaping covers HTML text and attribute values only. React `dangerouslySetInnerHTML`, Rails `raw` and `html_safe`, Angular `bypassSecurityTrust*` and Lit `unsafeHTML` all switch it off, and URL slots are never covered by escaping.
- **`JSON.stringify` is not an encoder**: embedding its output in `<script>` still breaks on a value containing `</script>`, which ends the script element from the HTML parser's point of view.
- **Sanitizing on input**: it corrupts data that is fine in most slots (the `O'Brien` problem), misses DOM-based sources, and cannot know the output slot. Encode on output, per slot.
- **WAFs and filters**: [OWASP treats these as an anti-pattern](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) for XSS. They lack the output context and never see DOM-based XSS. Consensus.
- **XSS defeats CSRF tokens**: same-origin script can read the token. See [[security/csrf]].

## Related Concepts

- [[security/same-origin-policy]]: XSS bypasses SOP by running inside the target origin rather than reading across origins
- [[security/csrf]]: CSRF tokens rely on SOP, so any XSS defeats them
- [[security/content-security-policy]]: the backup layer that limits what injected script can do once escaping fails

## References

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html): per-slot encoding rules, the slots no encoding fixes, framework escape hatches
- [OWASP DOM-based XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html): sources, sinks, safe replacements such as `textContent`
- [MDN Trusted Types API](https://developer.mozilla.org/en-US/docs/Web/API/Trusted_Types_API): policies, the two CSP directives, the default policy, browser support
- [React 19 upgrade guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide): "Error for javascript URLs in src and href"
