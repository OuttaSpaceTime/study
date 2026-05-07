---
title: Observable Error Handling
aliases:
- RxJS error handling
- catchError
- retry observable
- observable errors
- onError observable
tags:
- reactive
- rxjs
- error-handling
created: '2026-05-07'
updated: '2026-05-07'
source_skill: study-walkthrough
flashcard_ids: []
depth: 1
probe_sections:
- 'How error terminates a stream: subscription state after onError'
- 'catchError: signature, recovery pattern, and re-throw'
- 'retry vs retryWhen: immediate resubscription vs conditional backoff'
- Error in inner vs outer observable (flatMap/switchMap)
- 'Dead subscriber trap: subscribing after a subject has errored'
last_probed:
- 'How error terminates a stream: subscription state after onError'
- 'catchError: signature, recovery pattern, and re-throw'
- 'retry vs retryWhen: immediate resubscription vs conditional backoff'
- Error in inner vs outer observable (flatMap/switchMap)
- 'Dead subscriber trap: subscribing after a subject has errored'
review_interval: 3
next_review: '2026-05-10'
---

# Observable Error Handling

Errors in observables follow the [[reactive/observables]] contract. Once an error is emitted, the stream terminates. This shapes every error-handling pattern in reactive code.

## How error terminates a stream: subscription state after onError

When a source calls `subscriber.error(err)`:
1. The `error` callback on each subscriber fires
2. The subscription is automatically unsubscribed
3. No further `next` or `complete` events are delivered

```js
obs$.subscribe({
  next: v => console.log(v),
  error: e => console.error('stream died:', e),
  complete: () => console.log('done'), // never called on error
});
```

`complete` and `error` are mutually exclusive per the contract. `complete` does not fire on error.

If no `error` callback is provided, an unhandled observable error throws synchronously in some RxJS versions and is silently swallowed in others. Always provide an error handler.

## catchError: signature, recovery pattern, and re-throw

`catchError` intercepts an error and returns a replacement observable. The resulting stream continues from the replacement rather than terminating.

```js
source$.pipe(
  catchError(err => of('fallback value'))
).subscribe(console.log);
// if source errors: logs 'fallback value' then completes
```

To re-throw after a side effect:

```js
catchError(err => {
  logToSentry(err);
  return throwError(() => err);
})
```

`catchError` only catches errors from operators upstream of it in the pipeline. Operators downstream are unaffected.

## retry vs retryWhen: immediate resubscription vs conditional backoff

`retry(n)` resubscribes to the source observable up to n times when it errors. If the nth retry also errors, the error propagates.

```js
ajax('/api/data').pipe(
  retry(3)
).subscribe(handler);
```

Each retry is a fresh subscription. Cold observables re-execute the producer on each attempt and re-fire the request.

`retry({ delay: fn })` (RxJS 7) allows conditional logic such as exponential backoff:

```js
ajax('/api/data').pipe(
  retry({
    count: 3,
    delay: (err, attempt) => timer(attempt * 1000)
  })
).subscribe(handler);
```

Never use bare `retry()` without a count on observables that can error indefinitely. It will retry forever.

## Error in inner vs outer observable (flatMap/switchMap)

With `mergeMap` / `flatMap`, an error in an **inner** observable propagates to the outer by default and kills the entire pipeline.

```js
outer$.pipe(
  mergeMap(v => inner$(v)) // if inner$ errors, outer$ also errors and dies
).subscribe({ error: e => console.error('pipeline dead') });
```

To isolate inner errors and keep the outer alive, catch inside the mapping function:

```js
outer$.pipe(
  mergeMap(v =>
    inner$(v).pipe(
      catchError(err => of({ error: err })) // inner error becomes a value
    )
  )
).subscribe(handler);
```

This is the standard production pattern when processing a stream of requests where individual failures should not abort the whole pipeline.

The same applies to `switchMap` and `concatMap`. Inner errors propagate unless caught inside the mapping function.

## Dead subscriber trap: subscribing after a subject has errored

Cold observables re-execute the producer on each subscribe, so a new subscription may or may not hit the same error depending on the cause.

With **hot, multicast** observables (Subjects), new subscribers joining after an error receive nothing. The Subject is in a terminal state and emits no further events to anyone, including new subscribers.

```js
const subject = new Subject();
subject.error(new Error('boom'));

subject.subscribe({
  next: v => console.log(v),   // never fires
  error: e => console.error(e) // fires immediately with the stored error
});
```

Use a `BehaviorSubject` or `ReplaySubject` with upstream error handling if late subscribers need to recover. Never assume a subscribe call is safe just because another subscriber already handled the error.

## Related Concepts

- [[reactive/observables]]: the contract that governs error terminal behavior
- [[reactive/reactive-programming]]: operator pipeline context and flatMap variants
