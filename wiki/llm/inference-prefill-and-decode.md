---
title: Inference - Prefill and Decode
aliases:
- prefill decode
- LLM inference phases
- autoregressive generation
- why decode is slow
- num_predict mechanics
tags:
- llm
- inference
- performance
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
depth: 1
probe_sections:
- Inference vs training
- The two phases at a glance
- Prefill - one pass, parallel
- Decode - N passes, sequential
- Why output length dominates
- num_predict as the circuit breaker
- Rules of thumb for controlling prefill and decode cost
last_probed:
- Prefill - one pass, parallel
- Decode - N passes, sequential
- Rules of thumb for controlling prefill and decode cost
- Inference vs training
- The two phases at a glance
- Why output length dominates
- num_predict as the circuit breaker
review_interval: 14
next_review: '2026-06-28'
flashcard_ids: []
---

# Inference - Prefill and Decode

## TL;DR

A single LLM API call runs in two phases. **Prefill** processes the entire input prompt in one parallel GPU pass. **Decode** then generates output tokens one at a time, sequentially, each requiring its own forward pass through the model. Wall-clock time is dominated by decode, not prefill, because decode is N sequential passes where N is the number of output tokens. This is why output length matters more than prompt length for latency, and why `num_predict` (the output cap) is mandatory in production. It bounds the slow phase.

## Inference vs training

**Inference** is the general ML term for "running a trained model to produce output." Training is everything that happens during model development. Feeding examples, computing gradients, updating weights. Inference is everything that happens after. Every API call, every chat completion, every embedding lookup. When you `curl` an LLM endpoint, you're invoking an inference server. The model weights are frozen; you're just pushing tokens through them.

Inference is the phase that runs in production and the phase that costs money in operation.

## The two phases at a glance

Imagine sending the prompt `"Why is the sky"` (4 tokens) and asking the model to continue.

```
INPUT TOKENS         PREFILL                              DECODE
                     (1 pass, parallel)                   (N passes, sequential)
[Why, is, the, sky]  ──→ [run all 4 tokens through]  ──→  [step 1: produce "blue"]
                         the model in one pass             [step 2: produce "because"]
                                                           [step 3: produce "of"]
                                                           ... (one pass per output token)
```

Two phases. Two very different cost shapes. Most production gotchas come from confusing them.

## Prefill - one pass, parallel

Prefill takes all input tokens and runs them through the model **once**, in parallel. "Parallel" here means the GPU processes all input tokens together in a single forward pass, in roughly the same wall-clock time it would take to process one token (give or take attention's quadratic-in-length cost inside that pass).

What prefill produces:

1. A **probability distribution over the next token**. The model's prediction for what should follow the prompt.
2. The **KV cache for every input token**, stored in VRAM, used by every subsequent decode step. (See [[llm/kv-cache]].)

Prefill cost scales with prompt length, but the work happens in one batched compute. So a 5,000-token prompt is more expensive than a 50-token prompt, but it's still **one** GPU pass, not 5,000.

A useful mental image. Prefill is a chef *reading the entire ticket*. Eyes scan it all at once, taking it in.

## Decode - N passes, sequential

Decode is the loop that produces output. It runs **one forward pass per output token**, and each pass depends on the previous one. The basic step:

1. Read the probability distribution for the next token (produced by the previous step, or by prefill on step 1).
2. Sampler picks a token (see [[llm/sampling-knobs]]).
3. Compute K and V for the new token, append to the cache.
4. Run a forward pass producing the distribution for the next token.
5. Repeat until a stop token is sampled or `num_predict` is hit.

Each step is sequential. You cannot start step N+1 before step N has actually produced its token, because that token *is* the input to step N+1. There is no parallelism within a single response.

Mental image. Decode is a chef *plating one dish at a time, in order*. They cannot start dish 2 until dish 1 is on the counter.

## Why output length dominates

Order-of-magnitude numbers (rough; vary by hardware and model):

- A 35B model on a high-end GPU: **prefill ~2,000 tokens/sec, decode ~50 tokens/sec.**

Prefill is roughly 40× faster per token than decode, because prefill amortizes a single GPU pass across many tokens while decode pays one pass per token. Two example workloads:

| Workload | Input | Output | Prefill time | Decode time | Total |
|---|---|---|---|---|---|
| Confluence summarizer | 5,000 | 200 | ~2.5 s | ~4 s | **~6.5 s** |
| Creative writer | 50 | 2,000 | ~0.025 s | ~40 s | **~40 s** |

The summarizer has 100× the input but is **6× faster** than the writer. **Output length, not prompt length, is the dominant factor in wall-clock latency.**

This asymmetry shapes a number of production decisions:

- "Shorten the prompt to make it faster" is mostly false: it helps a little.
- "Shorten the output to make it faster" is mostly true: it helps a lot.
- "Streaming" exists because decode is so slow that the user wants partial results as soon as they're available.

## num_predict as the circuit breaker

Decode is bounded only by:

1. The model emitting a stop token.
2. The runtime's internal hard limit (often the model's max context length).

Both are dangerous as upper bounds. A model that gets stuck in a degenerate loop (repeating itself, hallucinating endlessly, drifting off-distribution from a bad sample at high temperature) will burn decode time until it runs out of context. That can be **thousands of tokens of useless output**, taking tens of seconds.

`num_predict` is the explicit cap. No matter what the model wants, stop after N output tokens. It directly bounds the worst-case wall-clock time of decode.

Practical guidance:

- **Always set `num_predict`.** Defaulting to "unlimited" is a footgun.
- **Cap to the smallest value the use case can tolerate.** JSON extraction: 512–1024. Short summary: 256–512. Long-form: 2048–4096. "Why so generous?": the model rarely uses the full budget; the cap is a safety net, not a target.
- **A hung extraction job is almost always missing `num_predict`.** A 30-second hang on a 200-token expected output is the textbook symptom.

## Rules of thumb for controlling prefill and decode cost

- **Latency budgets should be modeled in decode tokens, not prompt tokens.** Engineering effort to compress prompts pays back ~40× less than equivalent effort to compress outputs.
- **Streaming is a UX patch on a fundamental cost shape, not a free optimization.** It hides the slowness rather than removing it.
- **Tasks that can be done with shorter outputs (classification, extraction, structured fields) are dramatically faster than tasks that produce free-form text.**

## Related Concepts

- [[llm/kv-cache]]: the state structure produced by prefill and grown by decode, and why decode-with-cache is O(N) instead of O(N²).
- [[llm/sampling-knobs]]: the per-step controls that govern what each decode step samples.
- [[llm/serving-runtime-and-vram]]: what gets allocated when the model loads, before any inference happens.
- [[llm/embeddings-vs-embedding-layer]]: embedding-model calls have prefill but no decode loop, which is why they're cheap.
