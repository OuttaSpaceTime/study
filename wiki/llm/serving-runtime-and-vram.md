---
title: Serving Runtime and VRAM
aliases:
- LLM serving
- Ollama VRAM
- LLM model loading
- KEEP_ALIVE
- VRAM budget for LLMs
tags:
- llm
- ollama
- gpu
- infrastructure
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
depth: 1
probe_sections:
- The model is a file
- VRAM and why GPUs
- KEEP_ALIVE and the cold-start tax
- Multi-tenancy - what is shared, what is per-slot
- Same model, different num_ctx, two instances
- Sizing VRAM and choosing KEEP_ALIVE strategy
last_probed:
- The model is a file
- VRAM and why GPUs
- KEEP_ALIVE and the cold-start tax
- Multi-tenancy - what is shared, what is per-slot
- Same model, different num_ctx, two instances
- Sizing VRAM and choosing KEEP_ALIVE strategy
review_interval: 11
next_review: '2026-05-18'
flashcard_ids: []
---

# Serving Runtime and VRAM

## TL;DR

A trained model is a file of weights. Billions of numbers sitting on disk doing nothing. To run inference fast, the runtime loads those weights into **VRAM** (the GPU's onboard memory). Loading is expensive, so runtimes keep models warm for a configurable idle period. Multiple parallel requests share the loaded weights but each allocate their own KV cache, so VRAM budget is "weights once + cache per slot." If two apps request the same model with different `num_ctx`, they cannot share. The runtime is forced to load two separate instances. Most production "thrashing" comes from this rule alone.

## The model is a file

A trained LLM is just a binary file of learned parameters. For `qwen3.5:35b`, that's on the order of ~20 GB of weights (a 35-billion-parameter model at fp16 ≈ 70 GB, but quantized to int4/int8 in formats like GGUF it shrinks to ~20 GB). Sitting on disk it does nothing. No compute, no memory pressure.

Inference begins when the runtime (Ollama, vLLM, llama.cpp, TGI, etc.) **loads the file into VRAM**. From that point on, that GPU has the model's weights resident and can run requests against them.

## VRAM and why GPUs

Inference is dominated by **matrix multiplications**. The model's forward pass repeatedly multiplies the current state by the weight matrices in each layer. GPUs are built for this. Thousands of parallel arithmetic units optimized for matmul.

But the GPU can only multiply against weights that are already in VRAM (its onboard memory, separate from system RAM). Reading from system RAM over PCIe is many times slower than reading from VRAM. So the rule is simple. For inference to be fast, the entire model must fit in VRAM. If it doesn't, the runtime has to swap weights between RAM and VRAM mid-request, and throughput collapses.

Modern serving GPUs are sized accordingly. A typical inference card holds 24–96 GB of VRAM; a well-provisioned self-hosted Ollama server with 96 GB VRAM is enough for one large model plus several smaller ones plus their KV caches.

## KEEP_ALIVE and the cold-start tax

Loading 20 GB from disk into VRAM takes seconds on every "cold" request (the first request to an idle model). Pays this latency once.

Runtimes counter this with a **keep-alive** policy: once a model is loaded, hold it in VRAM for some idle window before evicting. Ollama exposes this as `OLLAMA_KEEP_ALIVE` (default ~5 minutes; production setups often raise it to `1h`). The effect is a step function:

```
First request after idle:    [load 20GB from disk] + [inference]   = slow
Next request 5 min later:    [inference]                            = fast
Next request 2 hours later:  model evicted → [load again] + [inf]   = slow again
```

The trade-off. Long `KEEP_ALIVE` means responsive subsequent requests but blocks VRAM that could host other models. Short `KEEP_ALIVE` evicts aggressively but reintroduces cold-starts.

**Concurrent first-callers share the load cost.** If five requests for the same un-loaded model arrive at once, the runtime loads it once and serves all five. They all wait for the load, but only one load happens.

## Multi-tenancy - what is shared, what is per-slot

When a single model serves multiple concurrent requests, the runtime is doing **batched inference**. Running several requests through the same forward passes. Ollama's `OLLAMA_NUM_PARALLEL` sets how many concurrent slots a loaded model offers.

The crucial detail. Across slots, **weights are shared, KV cache is per-slot**.

| Component | Shared across parallel slots? | Why |
|---|---|---|
| Model weights | Yes. One copy in VRAM, all slots read it | Weights are read-only constants; the GPU can run many forward passes against the same weight matrices |
| KV cache | No. Each slot has its own | Each request has its own context, growing token by token; one request's cache is meaningless to another |
| Activations | No. Each forward pass has its own working memory | Intermediate hidden states are temporary, per-pass |

So if `qwen3.5:35b` weights are ~20 GB and `NUM_PARALLEL=4`, the per-load VRAM budget is roughly:

```
20 GB (weights, shared)
 + 4 × cache_buffer_size  (one per slot, allocated at load time based on num_ctx)
 + small per-slot activations
```

For `num_ctx=65536` and a typical 35B model, each cache buffer can be 5–20 GB. Four slots can easily eat 50–80 GB of VRAM beyond the weights themselves. This is why `NUM_PARALLEL` is a tuned knob, not "set it to a big number."

See [[llm/kv-cache]] for the full cache-cost formula.

## Same model, different num_ctx, two instances

This is the production failure mode that shared-infra Ollama deployments most explicitly forbid:

> *Multiple instances of the same model with different context sizes cannot be reused and cause expensive load/unload cache misses.*

The mechanism: when a model is loaded, the runtime allocates the KV cache buffer once, sized to the requested `num_ctx`. That buffer stays put for the model's lifetime. If a later request asks for the same model but a different `num_ctx`, the existing instance is incompatible:

- A loaded instance with `num_ctx=8192` has a buffer too small for a request that wants 65K tokens of context.
- A loaded instance with `num_ctx=65536` has a buffer that wastes VRAM if every actual request is 8K.

The runtime has two choices. Either **load a second instance of the same model** (now ~40 GB of weights duplicated across two slots) or **evict and reload** (multi-second pause hitting every request during the cycle).

Both are bad. The fix is a convention, not a runtime feature. **all apps using the same model should agree on a single `num_ctx`**, ideally pinned server-side. A shared-infra Ollama deployment will typically pin something like `OLLAMA_CONTEXT_LENGTH=65536` and forbid per-request overrides for exactly this reason.

This rule cascades into model selection. If every app picks a different favorite model, the cache constantly thrashes between them. Standardize on a small set of shared models so the warm set stays warm.

## Sizing VRAM and choosing KEEP_ALIVE strategy

- **Cold-start latency is real.** First request after idle pays the load cost. Don't put cold-start in the user-visible critical path of a low-latency feature; warm the model with a tiny ping if needed.
- **VRAM budgeting starts with `weights + N × cache_buffer`.** Calculate before changing `NUM_PARALLEL` or `num_ctx`.
- **Same model, same `num_ctx` across apps.** This is the single most impactful shared-infra rule.
- **Prefer one large warm model over swapping among many.** Switching costs are measured in seconds per swap, multiplied by every cold request that hits during the swap.

## Related Concepts

- [[llm/kv-cache]]: what the per-slot cache actually contains and how its size scales with `num_ctx`.
- [[llm/inference-prefill-and-decode]]: how a single inference call uses the loaded weights and the cache.
- [[llm/sampling-knobs]]: the runtime knobs (`num_predict`, `temperature`, `think`) that govern decode behavior once the model is loaded.
- [[llm/embeddings-vs-embedding-layer]]: embedding models live alongside generative models on the same VRAM and follow the same tenancy rules.
