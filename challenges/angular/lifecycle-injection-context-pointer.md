---
wiki: angular/component-lifecycle
section: "Injection context: where inject() is valid and where it throws NG0203"
kind: write-code
env: node24
questions:
- Which four places count as valid injection contexts, and why is ngOnInit not one of them?
- What is the escape hatch when a method that runs after construction needs inject()?
created: 2026-07-03
---

## Brief

inject() reads an ambient "current injector" pointer that Angular only sets during specific call frames. Implement runInInjectionContext so the pointer is valid exactly for the duration of the callback.

## Stub

```js
let currentInjector = null;

function inject(token) {
  if (!currentInjector) throw new Error('NG0203: inject() must be called from an injection context');
  return currentInjector[token];
}

function runInInjectionContext(injector, fn) {
  // TODO: point currentInjector at injector only while fn runs, then restore it
}

const injector = { Router: 'RouterInstance' };

runInInjectionContext(injector, () => console.log('inside:', inject('Router')));

try {
  inject('Router');
} catch (e) {
  console.log('outside:', e.message);
}
```

## Solution

```js
let currentInjector = null;

function inject(token) {
  if (!currentInjector) throw new Error('NG0203: inject() must be called from an injection context');
  return currentInjector[token];
}

function runInInjectionContext(injector, fn) {
  const previous = currentInjector;
  currentInjector = injector;
  try {
    return fn();
  } finally {
    currentInjector = previous;
  }
}

const injector = { Router: 'RouterInstance' };

runInInjectionContext(injector, () => console.log('inside:', inject('Router')));

try {
  inject('Router');
} catch (e) {
  console.log('outside:', e.message);
}
```

## Expected Output

```
inside: RouterInstance
outside: NG0203: inject() must be called from an injection context
```
