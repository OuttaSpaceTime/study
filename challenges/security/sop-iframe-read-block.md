---
wiki: security/same-origin-policy
section: What SOP Actually Blocks
kind: predict-output
env: web
questions:
- The iframe text is visible on screen. Why can the user see it while the page's JS cannot read it?
- What other JS reads does SOP block besides cross-origin iframe DOM access?
created: 2026-07-03
---

## Brief

The sandbox attribute gives the iframe an opaque origin, so it stands in for a cross-origin page like bank.com. The frame renders its content on screen, then the embedding page's JS tries to read its DOM. Predict what the console shows.

## Stub

```html
<iframe id="f" sandbox srcdoc="<p>bank balance: 42</p>"></iframe>
```

```js
const f = document.getElementById("f");
f.addEventListener("load", () => {
  try {
    console.log("read:", f.contentWindow.document.body.textContent);
  } catch (e) {
    console.log("read blocked:", e.name);
  }
});
```

## Solution

```html
<iframe id="f" sandbox srcdoc="<p>bank balance: 42</p>"></iframe>
```

```js
const f = document.getElementById("f");
f.addEventListener("load", () => {
  try {
    console.log("read:", f.contentWindow.document.body.textContent);
  } catch (e) {
    console.log("read blocked:", e.name);
  }
});
```
