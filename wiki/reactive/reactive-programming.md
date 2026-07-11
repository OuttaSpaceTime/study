---
title: Reactive Programming
aliases:
- reactive programming paradigm
- reactive extensions paradigm
- streams programming
- reactive data streams
tags:
- reactive
- rxjs
- streams
created: '2026-05-07'
updated: '2026-05-07'
source_skill: study-walkthrough
flashcard_ids: []
probe_sections:
- 'Reactive programming definition: streams as first-class values'
- 'Stream anatomy: values, errors, and completion over time'
- 'Core operator categories: transform, filter, combine, flatten'
- 'flatMap/mergeMap: collapsing a stream of streams'
- Mental model shift from imperative to reactive
last_probed:
- 'Reactive programming definition: streams as first-class values'
- 'flatMap/mergeMap: collapsing a stream of streams'
- 'Stream anatomy: values, errors, and completion over time'
- 'Core operator categories: transform, filter, combine, flatten'
- Mental model shift from imperative to reactive
review_interval: 50
next_review: '2026-08-30'
---

# Reactive Programming

Reactive programming is programming with asynchronous data streams. A stream is a sequence of events ordered in time. Anything can be a stream. User clicks, HTTP responses, variable values, arrays, and timers are all streams.

You compose streams with operators rather than writing imperative control flow. The result is declarative pipelines that describe what data looks like at each stage, not when or how it arrives.

See [The Introduction to Reactive Programming You've Been Missing](https://gist.github.com/staltz/868e7e9bc2a7b8c1f754) by André Staltz.

## Reactive programming definition: streams as first-class values

A stream emits three types of events. It emits a **value** (next), an **error**, or a **completion** signal. You attach observers to react to each type asynchronously.

The core shift is to move from pulling data when you need it (calling a function, reading a variable) to declaring how data transforms as it flows through. Push-based rather than pull-based.

## Stream anatomy: values, errors, and completion over time

A stream can be visualized on a timeline:

```
--a--b--c--|-->   values a, b, c then complete
--a--b--X-->      values a, b then error X
--a-----------    infinite stream (no completion)
```

Each event arrives asynchronously. You handle each type with a separate callback. Pass `next`, `error`, and `complete` handlers to `subscribe`. The contract governing these is in [[reactive/observables]].

## Core operator categories: transform, filter, combine, flatten

Operators are pure functions that take a stream and return a new stream.

**Transform:**
- `map(fn)`: apply fn to each value
- `scan(fn, seed)`: running accumulator; like `reduce` but emits each intermediate value

**Filter:**
- `filter(predicate)`: drop values that fail the predicate
- `take(n)`: complete after n values
- `startWith(value)`: prepend a value before the first emission

**Combine:**
- `merge(streamB)`: interleave two streams; emits whenever either emits
- `combineLatest(streamB)`: emit the latest pair whenever either emits; waits until both have emitted at least once

**Flatten:**
- `flatMap` / `mergeMap(fn)`: for each value, call fn to get a new stream, then merge all resulting streams into one

## flatMap/mergeMap: collapsing a stream of streams

When mapping each value to an Observable, `map` produces a stream-of-streams (metastream). `flatMap` collapses it by subscribing to each inner observable and merging the results.

```js
// clickStream → requestStream (metastream) → responseStream (flat)
const responseStream = clickStream.pipe(
  flatMap(click => ajax('/api/users'))
);
```

Without `flatMap`, each click would produce an unsubscribed inner Observable. With it, each click fires the request and its response flows out as a plain value.

Related variants:
- `switchMap`: cancels the previous inner observable when a new value arrives
- `concatMap`: queues inner observables; waits for each to complete before starting the next
- `exhaustMap`: ignores new values while an inner observable is active

## Mental model shift from imperative to reactive

In imperative code you write "when X happens, do Y, then check Z."

In reactive code you declare "the output stream is X combined with Y, filtered by Z."

This removes scattered event listeners, nested callbacks, and manual state variables for tracking what fired last. State lives in the pipeline, not in variables you update by hand.

The tradeoff is that reactive pipelines are harder to debug. Stack traces point at operators, not your code. Marble diagrams are the standard visualization tool.

## Related Concepts

- [[reactive/observables]]: the core primitive (lazy, subscribable, contract-bound)
- [[reactive/observable-error-handling]]: how errors propagate and terminate streams
