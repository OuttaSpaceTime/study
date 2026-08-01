---
title: Component lifecycle
aliases:
- angular lifecycle hooks
- ngOnInit vs constructor
- afterNextRender
- angular injection context
tags:
- angular
- frontend
- lifecycle
- dependency-injection
created: '2026-05-08'
updated: '2026-05-08'
source_skill: study-walkthrough
flashcard_ids: []
---

# Component lifecycle

The lifecycle hooks answer three operational questions. *When does a hook fire?* *What is safe to read inside it?* *Where can I call `inject()`?* This page covers the firing order, the constructor / ngOnInit split, the Content / View distinction, the injection context rules, and how `afterRender` / `afterNextRender` fit in.

## TL;DR

- The constructor runs first. DI is available, `@Input` values are not.
- `ngOnInit` is the first hook where decorator-based `@Input` values are settled.
- `*Init` hooks fire once. `*Checked` hooks fire on every change detection run.
- `ngAfterContentInit` fires before `ngAfterViewInit` on the same component. Across the tree, init proceeds depth-first post-order, so a child's `ngAfterViewInit` runs before its parent's.
- `inject()` requires an injection context. Constructor body, field initializer, factory, and `runInInjectionContext` are valid. `ngOnInit` and the other lifecycle methods are not.
- `afterNextRender` runs after the browser commits the DOM. `ngAfterViewInit` runs before paint.

## Init Order: Depth-First Post-Order Across the Tree

On first render, hooks fire in this order on a component with decorator inputs.

```
constructor
ngOnChanges        (only if @Input bindings exist)
ngOnInit
ngDoCheck
ngAfterContentInit
ngAfterContentChecked
ngAfterViewInit
ngAfterViewChecked
```

Across a component tree, the *Init* and *Checked* hooks are bottom-up. Given:

```html
<parent>
  <child>
    <grandchild/>
  </child>
</parent>
```

The View hooks fire in post-order. The grandchild's `ngAfterViewInit` runs before the child's, which runs before the parent's. The reason is that "View" includes every descendant component instance, so a parent's view cannot be considered initialized until all its descendants are.

The *Checked* hooks (`ngDoCheck`, `ngAfterContentChecked`, `ngAfterViewChecked`) repeat on every change detection cycle. `ngOnChanges` fires whenever bound `@Input` values change, batching all changes from one CD run into a single `SimpleChanges` map.

> [Note] Signal-based `input()` does not trigger `ngOnChanges`. Migrating an `@Input()` to `input()` silently disables the hook for that input. Use `effect()` or `computed()` to react to signal input changes.

## constructor vs ngOnInit: Why @Input Is Undefined in the Constructor

The constructor runs at JS class instantiation time. Angular instantiates the component, then applies `@Input` bindings, then fires `ngOnChanges`, then `ngOnInit`. Reading an `@Input`-decorated property in the constructor returns `undefined` because the binding has not been applied yet.

```ts
@Component({...})
export class FooComponent implements OnInit {
  @Input() name!: string;
  private router = inject(Router);   // valid: field initializer is an injection context

  constructor() {
    console.log(this.name);          // undefined
  }

  ngOnInit() {
    console.log(this.name);          // 'whatever the parent bound'
  }
}
```

Use the constructor for DI and field defaults that do not depend on inputs. Use `ngOnInit` for setup that needs input values, including any HTTP request or initial state derived from inputs.

> [Note] Signal-based inputs (`input()`, stable since Angular 17.2) ARE readable in field initializers, since they are signals and reading the signal in the initializer just returns the initial value. Code that uses `input()` exclusively often skips `ngOnInit` entirely.

## ngOnChanges: Fires on First Render and Batches All Input Changes

Two things developers commonly get wrong about `ngOnChanges`.

**It does fire on the first render**, between the constructor and `ngOnInit`, as long as the component declares any decorator `@Input()`. Components with zero inputs never see `ngOnChanges`.

**It fires once per change detection cycle, not once per input.** All input changes from a single CD run are batched into one `SimpleChanges` map. If the parent updates three inputs in the same tick, `ngOnChanges` is called once with three keys in the map.

```ts
ngOnChanges(changes: SimpleChanges) {
  if (changes['user']) {
    // first render: changes['user'].firstChange === true
    // later renders: firstChange === false
  }
}
```

`firstChange` on a `SimpleChange` distinguishes the initial binding from a later update.

## Content vs View Hooks: Which Decorator Becomes Available Where

| Decorator | Where the queried element lives | First available in |
|---|---|---|
| `@ContentChild` | projected via `<ng-content>` | `ngAfterContentInit` |
| `@ViewChild` | the component's own template | `ngAfterViewInit` |

The names line up. **Content**Child becomes available in after**Content**Init. **View**Child becomes available in after**View**Init.

The reason they differ. Content is "what the parent passed in via `<ng-content>`." It was already constructed by the parent before this component started. View is "this component's own template, including every descendant component fully initialized." View has more to wait for, so it fires later.

Querying a `@ViewChild` inside `ngAfterContentInit` returns `undefined`. Querying a `@ContentChild` inside `ngOnInit` returns `undefined` for the same reason.

## Injection Context: Where inject() Is Valid and Where It Throws NG0203

`inject()` is a plain function that reads from a "current injector" pointer Angular maintains. The pointer is only valid inside specific call frames. Outside them, `inject()` throws `NG0203: inject() must be called from an injection context`.

**Valid injection contexts.**

1. The constructor body of an `@Injectable` or component class.
2. A class field initializer (e.g. `private router = inject(Router)`).
3. A factory function (e.g. `useFactory: () => …`).
4. Inside a `runInInjectionContext(injector, fn)` callback.

**Not valid.** `ngOnInit` and the other lifecycle methods. Event handlers. Subscribe callbacks. Anything that runs after construction completes.

**Escape hatch.** Capture the `Injector` during construction, then re-enter it later.

```ts
export class FooComponent {
  private injector = inject(Injector);

  someLaterMethod() {
    runInInjectionContext(this.injector, () => {
      const router = inject(Router);   // valid again
    });
  }
}
```

This pattern is rarely needed. The cleaner approach is to inject everything you might need in the constructor or a field initializer.

## afterNextRender vs ngAfterViewInit: Post-Paint vs Pre-Paint Timing

`ngAfterViewInit` fires after Angular has built the component's view in memory but **before** the browser has painted. DOM measurements taken inside `ngAfterViewInit` may be pre-layout and trigger forced reflows when read.

`afterNextRender(cb)` fires once, **after** the browser has committed the DOM and painted. It is the right hook for post-paint DOM reads, third-party library handoffs that need real layout, and any code that needs the rendered pixel positions. `afterEveryRender(cb)` (renamed from `afterRender` in v19) fires after every render and should be used sparingly.

Both are application-wide standalone functions, [per the Angular docs](https://angular.dev/api/core/afterNextRender). They must be called in an injection context, typically the constructor. They run on the browser only and are skipped during SSR / prerender.

```ts
@Component({...})
export class ChartComponent {
  private host = inject(ElementRef);

  constructor() {
    afterNextRender(() => {
      const width = this.host.nativeElement.clientWidth;   // real, painted width
      this.initChart(width);
    });
  }
}
```

**Synchronous injection context inside the callback.** Angular wraps each render callback invocation in `runInInjectionContext`, so `inject()` works inside the callback body, but only synchronously. The first `await` or `setTimeout` ends the wrapped frame and subsequent `inject()` calls throw `NG0203`. Capture an `Injector` upfront if the callback needs DI after an `await`.

**Phases.** `afterNextRender` accepts a phase option (`earlyRead`, `write`, `mixedReadWrite`, `read`) so reads and writes can be ordered to avoid layout thrashing.

## Related Concepts

- [[angular/change-detection]]: how Angular decides when to re-check component bindings, including `OnPush` and the role of `ngDoCheck` / `*Checked` hooks.
- [[angular/signals-and-change-detection]]: signals-era reactivity, `effect()`, and how `input()` interacts with the lifecycle hooks above.

## References

- [Component lifecycle, angular.dev](https://angular.dev/guide/components/lifecycle): canonical hook list, firing order, constructor vs ngOnInit, render callbacks.
- [afterNextRender API, angular.dev](https://angular.dev/api/core/afterNextRender): phases, injection context behavior, browser-only execution.
- [Side effects (effect / afterRenderEffect), angular.dev](https://angular.dev/guide/signals/effect): signals-era reactive lifecycle and how it composes with render callbacks.
