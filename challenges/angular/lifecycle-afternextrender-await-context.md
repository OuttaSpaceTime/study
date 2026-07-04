---
wiki: angular/component-lifecycle
section: "afterNextRender vs ngAfterViewInit: post-paint vs pre-paint timing"
kind: predict-output
env: node24
questions:
- When does afterNextRender fire relative to browser paint, and what kind of work belongs there instead of in ngAfterViewInit?
- Why does inject() stop working after the first await inside a render callback, and what should the callback capture upfront instead?
created: 2026-07-03
---

## Brief

Angular wraps each render callback invocation in runInInjectionContext, so inject() works inside the callback body. The wrapper restores the pointer as soon as the synchronous part of the callback returns. Predict what an async callback sees before and after its first await.

## Stub

```js
let currentInjector = null;

function inject(token) {
  if (!currentInjector) throw new Error('NG0203: inject() must be called from an injection context');
  return currentInjector[token];
}

function afterNextRender(callback) {
  currentInjector = { ElementRef: 'HostElement' };
  try {
    callback();
  } finally {
    currentInjector = null;
  }
}

afterNextRender(async () => {
  console.log('sync:', inject('ElementRef'));
  await null;
  try {
    inject('ElementRef');
  } catch (e) {
    console.log('after await:', e.message);
  }
});
```

## Solution

```js
let currentInjector = null;

function inject(token) {
  if (!currentInjector) throw new Error('NG0203: inject() must be called from an injection context');
  return currentInjector[token];
}

function afterNextRender(callback) {
  currentInjector = { ElementRef: 'HostElement' };
  try {
    callback();
  } finally {
    currentInjector = null;
  }
}

afterNextRender(async () => {
  console.log('sync:', inject('ElementRef'));
  await null;
  try {
    inject('ElementRef');
  } catch (e) {
    console.log('after await:', e.message);
  }
});
```

## Expected Output

```
sync: HostElement
after await: NG0203: inject() must be called from an injection context
```
