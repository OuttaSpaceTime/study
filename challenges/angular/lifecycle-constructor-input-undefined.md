---
wiki: angular/component-lifecycle
section: "constructor vs ngOnInit: why @Input is undefined in the constructor"
kind: predict-output
env: ts-node24
questions:
- What does Angular do between running the constructor and calling ngOnInit?
- Why are signal-based input() values already readable in a field initializer?
created: 2026-07-03
---

## Brief

Angular instantiates the component class, then applies @Input bindings, then calls ngOnInit. This snippet replays that exact sequence in plain TypeScript. Predict both log lines.

## Stub

```ts
class FooComponent {
  name: string | undefined;

  constructor() {
    console.log(`constructor: ${this.name}`);
  }

  ngOnInit() {
    console.log(`ngOnInit: ${this.name}`);
  }
}

const component = new FooComponent();
component.name = 'Ada';
component.ngOnInit();
```

## Solution

```ts
class FooComponent {
  name: string | undefined;

  constructor() {
    console.log(`constructor: ${this.name}`);
  }

  ngOnInit() {
    console.log(`ngOnInit: ${this.name}`);
  }
}

const component = new FooComponent();
component.name = 'Ada';
component.ngOnInit();
```

## Expected Output

```
constructor: undefined
ngOnInit: Ada
```
