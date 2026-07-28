---
title: Observables
aliases:
- Observable
- RxJS observable
- cold observable
- hot observable
- subscribe observable
tags:
- reactive
- rxjs
- observables
created: '2026-05-07'
updated: '2026-05-07'
source_skill: study-walkthrough
flashcard_ids: []
review_interval: 14
next_review: '2026-08-01'
---

# Observables

An Observable is a lazy, push-based data source. It emits values, errors, and a completion signal to subscribers over time.

## Why observables are lazy and what subscribe triggers

The producer function inside an Observable does not run when the Observable is created. It runs when `subscribe` is called.

```js
const obs$ = new Observable(subscriber => {
  console.log('producer running');
  subscriber.next(1);
  subscriber.complete();
});
// nothing logged yet

obs$.subscribe(v => console.log(v));
// logs: 'producer running', 1
```

Each `subscribe` call creates an independent execution. Two subscribers get two separate runs of the producer with no shared state. This contrasts with a Promise, which runs its executor immediately on construction and shares the result with all `.then` handlers.

## The Observable Contract: grammar and serial delivery rule

Every Observable must obey:

```
onNext* (onError | onComplete)?
```

In plain terms:
- Zero or more `next` emissions
- At most one terminal event: either `error` or `complete`, never both
- Nothing emitted after the terminal event

The contract also mandates serial delivery. Notifications must be issued one at a time, never concurrently. Cross-thread emissions are legal if a happens-before relationship is established.

Violations such as emitting after `complete` or concurrent `next` calls cause undefined behavior downstream. Operators and subscribers rely on the contract holding.

**Source:** [ReactiveX Observable Contract](https://reactivex.io/documentation/contract.html)

## Cold vs hot observables: independent vs shared execution

**Cold:** the producer is created fresh per subscriber. Each subscriber gets the full sequence from the start. HTTP request observables are cold. Each subscriber fires its own request.

```js
// cold: each subscriber triggers its own ajax call
const req$ = ajax('/api/data');
req$.subscribe(a => console.log('A', a));
req$.subscribe(b => console.log('B', b)); // second independent request
```

**Hot:** the producer exists independently of subscribers. Subscribers tap into an ongoing sequence at the current position. Mouse event observables are hot. Clicks happen whether or not anyone is subscribed.

The distinction matters when you want to avoid duplicate side effects. Use `share()` or `shareReplay()` to convert a cold observable to hot so multiple subscribers share one execution.

## Subscription lifecycle: what subscribe returns and how teardown works

`subscribe` returns a `Subscription` object with an `unsubscribe()` method. Calling it stops delivery and runs any teardown logic registered inside the producer.

```js
const sub = interval(1000).subscribe(v => console.log(v));
setTimeout(() => sub.unsubscribe(), 3500); // logs 0, 1, 2 then stops
```

The producer registers teardown by returning a cleanup function:

```js
new Observable(subscriber => {
  const id = setInterval(() => subscriber.next(Date.now()), 1000);
  return () => clearInterval(id); // runs on unsubscribe, complete, or error
});
```

Failing to unsubscribe from long-lived observables is the primary source of memory leaks in reactive code. In Angular this is addressed with `takeUntil(destroy$)` or the `async` pipe, both of which unsubscribe automatically.

## Related Concepts

- [[reactive/reactive-programming]]: the paradigm and operator toolkit
- [[reactive/observable-error-handling]]: what happens when the producer calls subscriber.error()
