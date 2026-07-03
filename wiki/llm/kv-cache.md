---
title: KV Cache
aliases:
- KV cache
- key-value cache
- attention cache
- num_ctx mechanics
- why decode is O(n)
tags:
- llm
- inference
- attention
- transformer
- archived
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
probe_sections:
- What attention is doing - Q, K, V
- Where the prediction comes from - K/V are inputs, not the output
- Why two vectors per token, not one
- Why K and V are cached but not Q
- The cache grows by one entry per decode step
- Cost formula
- Without the cache - O(N²)
- num_ctx is the cache buffer size
last_probed:
- Where the prediction comes from - K/V are inputs, not the output
- What attention is doing - Q, K, V
- Why two vectors per token, not one
- Cost formula
- Without the cache - O(N²)
- num_ctx is the cache buffer size
- Why K and V are cached but not Q
- The cache grows by one entry per decode step
review_interval: 10
next_review: '2026-07-03'
flashcard_ids: []
---

# KV Cache

## TL;DR

The KV cache is a per-request VRAM buffer that lets a transformer skip recomputing the K (Key) and V (Value) vectors for every past token at every decode step. It turns total decode work from O(N²) to O(N), trading VRAM for compute. The cache size at full context can rival or exceed the model weights themselves, which is why `num_ctx` (the maximum cache length) is a load-time allocation decision and changing it across requests forces the runtime to load a new model instance.

## What attention is doing - Q, K, V

The transformer's attention layer is, mechanically, a **tiny per-step search engine** running inside each layer of the model. Every token, in every layer, produces three vectors computed by multiplying the token's hidden state against three learned weight matrices `Wq`, `Wk`, `Wv`:

- **Q (Query)**: what the *current* token is looking for in past context.
- **K (Key)**: what *each* token advertises about itself.
- **V (Value)**: what *each* token contributes if attended to.

A concrete walk. Context is `"The cat sat on the"`. The model is producing the next token.

1. The current position generates a query vector `Q`. Informally, "given I'm coming after `'The cat sat on the'`, what should follow?"
2. Each past token (`The`, `cat`, `sat`, `on`, `the`) has a `K` and `V` already computed and stored.
3. Compute dot products: `Q · K_The`, `Q · K_cat`, `Q · K_sat`, `Q · K_on`, `Q · K_the`. High dot product = "this token's K matches what I'm looking for."
4. Softmax the dot products into attention weights, e.g. `[0.05, 0.40, 0.30, 0.10, 0.15]`.
5. Output of the attention layer = weighted sum of V vectors: `0.05·V_The + 0.40·V_cat + ...`.

That blended vector flows to the next layer. Each transformer layer has its own attention; the model has dozens of layers, so this happens dozens of times per token.

## Where the prediction comes from - K/V are inputs, not the output

A common confusion is "the sentence is passed through the model and K/V predict the next token." Two corrections.

**K/V are per-layer, computed and consumed inside the forward pass, not as a separate step.** The model is a stack of layers run in one pass. At every layer, each token produces its own Q/K/V from that layer's hidden state, and that layer's attention consumes them immediately; the blended output flows up to the next layer, which has its own independent K/V. So there is no single global K/V. There is one cache per layer (that is the `× num_layers` in the cost formula).

**The next-token prediction does not come from K/V directly. It comes from the last position's final hidden state.** K and V are attended-to inputs. The current position's Q reads them to build a context-blended representation. The actual prediction is produced by the hidden state at the **last position**, after it has flowed through all layers, hitting the output (unembedding) matrix to produce logits, which the sampler turns into a token. The cached K/V of past tokens shape that last-position representation; they are inputs to the prediction, not the prediction itself.

So a prompt pass (prefill) does two things at once. Every token at every layer writes its K/V into the per-layer caches, and the last position's final hidden state produces the first next-token distribution. Decode then repeats one token at a time. Its Q attends against the cached K/V, its own K/V append, and its last-position output predicts the following token. See [[llm/inference-prefill-and-decode]] for the phase split.

## Why two vectors per token, not one

K and V answer different questions:

- K = "**Am I relevant?**": the matching role.
- V = "**What do I contribute if you look at me?**": the content role.

If the model used a single vector for both, it would be constrained. Any token relevant to a query would have to deliver content shaped by the same vector. Separating K and V lets the model learn an asymmetry between *being findable* and *being useful*. The token `cat`'s K is shaped to match queries like "looking for the noun something sat on"; its V carries semantic content (cat-meaning, plurality, prior-context interactions). Different jobs, different vectors.

This is a learned architectural choice. The K and V projection matrices are independent during training.

## Why K and V are cached but not Q

Q is **per-current-token only**. When the model is decoding step N, it computes `Q_N` for that step and uses it once. The dot products against all past K, the resulting weighted sum over all past V. Q_N is never reused after step N completes; future decode steps will compute their own Q_{N+1}, Q_{N+2} from their own current-token hidden state.

K and V, however, **describe past tokens, which don't change as the sequence grows.** Once `K_cat` and `V_cat` are computed, they remain valid descriptors of `cat` for every future decode step. Caching them once and reading them many times is a clear win. Caching Q would be wasted memory. There's no reuse.

## The cache grows by one entry per decode step

Sequence of cache states for prompt `"The cat sat on the"` (5 tokens) generating 3 output tokens:

| Phase | Step | Cache contents | Cache size |
|---|---|---|---|
| Prefill | | K/V for: The, cat, sat, on, the | 5 |
| Decode | 1 | append K/V for new token (`mat`) | 6 |
| Decode | 2 | append K/V for new token (`.`) | 7 |
| Decode | 3 | append K/V for new token (`END`) | 8 |

Each decode step:

1. Compute K and V for the just-generated token; append to the cache.
2. Compute Q for the current position.
3. Compute attention against the entire (now grown) cache.
4. Output flows through the rest of the model; sample next token.

The cache strictly grows during a request. It never shrinks. Every past token's K and V can still be attended to at any future step, so the model is not allowed to forget them. (Architectures like sliding-window attention break this rule deliberately to bound memory.)

## Cost formula

The formula for cache memory at full context, per request slot:

```
context_length × num_layers × hidden_dim × 2 (K and V) × precision_bytes
```

A worked example for a 35B-class model at full 65K context:

| Factor | Value |
|---|---|
| `context_length` | 65,536 |
| `num_layers` | ~60 |
| `hidden_dim` | ~5,120 |
| K and V | 2 |
| `precision_bytes` (fp16) | 2 |

That works out to `65,536 × 60 × 5,120 × 2 × 2 ≈ 80 GB`.

That's a worst-case full-context approximation, and modern architectures use **Grouped-Query Attention (GQA)** or **Multi-Query Attention (MQA)** to share K/V across multiple Q heads, cutting the cache by 4–8×. Quantizing the cache to fp8 halves it again, int4 again. So real numbers are smaller. But the *shape* of the formula holds. Cache scales linearly with context length and grows with the model's depth and width.

For long-context requests on large models, the KV cache can be comparable to or larger than the model weights themselves.

## Without the cache - O(N²)

Why the cache exists at all. Without it, every decode step would have to recompute K and V for *every* token in the context from scratch:

```
Step 1 (context = 5):   recompute 5 K/V pairs + Q
Step 2 (context = 6):   recompute 6 K/V pairs + Q   ← steps 1..5 redundant
Step 3 (context = 7):   recompute 7 K/V pairs + Q   ← even more redundant
...
Step N (context = 5+N): recompute 5+N K/V pairs + Q
```

Total K/V computations sum to `5 + 6 + 7 + ... + (5+N) = O(N²)`. Generating 1,000 tokens would do ~500,000 redundant K/V computations.

With the cache, each step computes K and V for **only the new token**, attends against the prior cached entries, and appends. Total K/V work drops to `O(N)`.

| Approach | Total decode K/V work for N output tokens |
|---|---|
| No cache | O(N²). Quadratic |
| With cache | O(N). Linear |

The dot products inside attention are still `O(context_length)` per step (you read all cached K and V), so total attention reads remain `O(N²)`. But cache reads are cheap memory operations; recomputing K and V is expensive matmul. The cache trades VRAM for compute and the trade is enormously favorable.

This is *the* reason LLMs are usable for long outputs. Without it, a 1,000-token completion would take orders of magnitude longer.

## num_ctx is the cache buffer size

The cache lives in a VRAM buffer that must be **pre-allocated when the model is loaded**, big enough to hold a full-context cache. The size of that buffer is exactly what `num_ctx` (or `OLLAMA_CONTEXT_LENGTH`) specifies.

Two consequences for production:

1. **`num_ctx` is a load-time decision, not a per-request one.** A model loaded with `num_ctx=8192` cannot serve a request that needs 65K context. Its buffer is too small. The runtime would have to evict and reload with a bigger buffer, hitting every request during the cycle.
2. **Two apps using the same model with different `num_ctx` cannot share an instance.** They force the runtime into either two loaded copies of the same weights (~2× VRAM) or load/unload thrashing. See [[llm/serving-runtime-and-vram]] for the full failure mode.

`num_ctx` also caps total request length. The bound is `prompt_tokens + output_tokens ≤ num_ctx`; exceed it and the runtime truncates or errors.

## Sizing num_ctx in practice

Because cache scales linearly with context, `num_ctx` is a real lever:

- Large `num_ctx` (32K–128K): needed for RAG with many retrieved chunks, long documents, multi-turn agents with extensive history.
- Small `num_ctx` (2K–8K): plenty for chat completions, classification, short extraction. Frees VRAM for more parallel slots or other models.

The right number is "the smallest value the longest request actually needs." Setting it too high wastes VRAM continuously; setting it too low fails some requests outright.

As a concrete example, a 96 GB VRAM server hosting a 100B+ parameter model at `OLLAMA_CONTEXT_LENGTH=65536` typically has no headroom for a second context size. The cache for that model at that context already eats a large slice of VRAM, so per-request overrides have to be forbidden.

## Related Concepts

- [[llm/inference-prefill-and-decode]]: the cache is filled during prefill and grown during decode.
- [[llm/serving-runtime-and-vram]]: `num_ctx` interacts with `OLLAMA_NUM_PARALLEL`: each parallel slot allocates its own cache buffer.
- [[llm/sampling-knobs]]: `num_predict` caps how far the cache can grow during one request.
- [[llm/embeddings-vs-embedding-layer]]: embedding models do not run a decode loop, so they don't grow a cache the same way.
