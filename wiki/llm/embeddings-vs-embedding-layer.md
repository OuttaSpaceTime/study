---
title: Embeddings vs Embedding Layer
aliases:
- embedding model
- embedding layer
- semantic search
- RAG flow
- two meanings of embedding
- nomic-embed-text
tags:
- llm
- embeddings
- rag
- retrieval
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
depth: 1
probe_sections:
- The two meanings, untangled
- Meaning 1 - the embedding layer
- Meaning 2 - embedding models
- Cost asymmetry vs generative LLMs
- The RAG data flow
- Why retrieval is necessary, not optional
last_probed:
- The two meanings, untangled
- Meaning 1 - the embedding layer
- Meaning 2 - embedding models
- Cost asymmetry vs generative LLMs
- The RAG data flow
- Why retrieval is necessary, not optional
---

# Embeddings vs Embedding Layer

## TL;DR

The word "embedding" means two different things in LLM systems and they get conflated routinely. **Meaning 1**: the *embedding layer* inside every transformer that maps token IDs to internal vectors at the model's input — machinery, not user-facing. **Meaning 2**: dedicated *embedding models* (a separate model class, e.g. `nomic-embed-text`) whose entire output is one vector per text input, used for semantic search, retrieval, and RAG. Embedding models run a single forward pass with no decode loop — they are dramatically cheaper than generative LLMs per call. Most "AI features" use both: one embedding model call per query plus per ingested document, plus one generative LLM call per query for the final answer.

## The two meanings, untangled

The collision happens because both senses involve "turning text into vectors" — but they happen at very different scopes and serve very different purposes.

| Aspect | Embedding *layer* (Meaning 1) | Embedding *model* (Meaning 2) |
|---|---|---|
| Where it lives | Inside every transformer's input | Separate model, separate API call |
| Output | A vector *per token*, internal | One vector per *text*, externalized |
| User-facing? | No — hidden machinery | Yes — that vector is the API response |
| Used for | The first layer of any LLM forward pass | Semantic search, RAG, similarity, clustering |
| Cost shape | Negligible (one matrix lookup) | One full forward pass per call |

When a typical self-hosted Ollama deployment is described as "running embeddings and LLM interactions," both nouns refer to **Meaning 2** vs generative-LLM use cases on the same infra. The embedding layer (Meaning 1) is invisible — it's just part of how the generative LLM works internally.

## Meaning 1 - the embedding layer

Every transformer model has, as its first computational step, a learned **embedding matrix** of shape `[vocab_size × hidden_dim]`. It's a giant lookup table mapping token IDs to fixed-size vectors:

```
Tokenize:     "The cat sat"        → [12, 4567, 89]   (token IDs)
Embed:        [12, 4567, 89]       → [vec_12, vec_4567, vec_89]   (one vector each, ~5,120-dim)
Transformer:  [vec_12, vec_4567, vec_89]   → ... runs through 60+ attention/MLP layers ...
```

The embedding layer's output is the **per-token internal representation** that the rest of the model operates on. It's sometimes called the "input embedding" to disambiguate from the second meaning. You never see these vectors via the API — they're internal state of any LLM forward pass, including in generative LLMs and inside embedding models alike.

This is the "embedding" your prompt gets turned into during prefill.

## Meaning 2 - embedding models

An **embedding model** is a separate, purpose-built model whose entire job is: take an arbitrary piece of text, produce **one vector** representing the meaning of that text. Examples: `nomic-embed-text`, `mxbai-embed-large`, OpenAI's `text-embedding-3-small`, Cohere's embed family.

Internally, an embedding model:

1. Tokenizes the input text.
2. Runs all tokens through its transformer in one forward pass (essentially equivalent to prefill — see [[llm/inference-prefill-and-decode]]).
3. **Pools** the per-token output vectors into a single text-level vector — typically by mean-pooling, taking the `[CLS]` token's vector, or last-token pooling.
4. Optionally normalizes the result to unit length.

The output is a single vector, often 384, 768, or 1024 dimensions long.

Crucially, **there is no decode loop, no sampler, no autoregressive generation.** No `temperature`, no `num_predict`, no `think`. One forward pass produces the full result. That makes embedding models **dramatically cheaper per call** than generative LLMs.

## Cost asymmetry vs generative LLMs

Per-call cost picture, big-picture:

| Model class | Compute | Wall-clock per call | Output |
|---|---|---|---|
| Embedding model | One forward pass through a small model (often <1 GB, ~100M params) | Tens of milliseconds | One vector |
| Generative LLM | Prefill + N decode steps, one forward pass per output token, on a big model (~20+ GB) | Hundreds of ms to tens of seconds | A stream of tokens |

The asymmetry is one to two orders of magnitude per call, and the gap widens with output length. This is the architectural justification for the **two-model production pattern**: do the cheap thing many times (search), then the expensive thing once (answer).

## The RAG data flow

**RAG** (Retrieval-Augmented Generation) is the canonical pattern that uses both model classes. It runs in two phases at two different times:

### Ingestion (offline, async, runs whenever content changes)

```
Source document  →  split into chunks (e.g. ~500 tokens each)
                          │
                          ▼
                   for each chunk:
                          │
                          ▼
                   [Embedding model]  →  vector
                          │
                          ▼
                   Store {vector, chunk_text, source_id, ...} in vector DB
```

This is high *aggregate* cost (every page processed) but each call is cheap. Done once per content update.

### Query (online, synchronous, runs every user question)

```
User query
    │
    ▼
[Embedding model]  →  query vector
    │
    ▼
Vector DB cosine-similarity search  →  top-K chunks
    │
    ▼
[Generative LLM]  ←  prompt: "{retrieved chunks}\n\nUser asked: {query}"
    │
    ▼
Answer
```

Each query costs:

- One embedding-model call (cheap, ~tens of ms).
- One vector DB search (cheap, milliseconds).
- One generative-LLM call (the expensive one — but on a *retrieved*, focused prompt rather than the full corpus).

The vector DB stores the original text alongside each vector (or a pointer to it). Vectors are not invertible to text — you look up vectors by similarity and **read back the stored text** that was embedded to produce them.

## Why retrieval is necessary, not optional

A natural question: "why not just feed all our documents to the LLM directly and ask it to find the answer?" The answer is mechanical, not stylistic.

1. **Context size cap.** A typical knowledge base is millions of tokens — Confluence wikis, codebases, transcripts. Even the largest production context windows (~64K–200K tokens) can't hold all of it. Retrieval shrinks the input to the relevant slice.
2. **Prefill cost scales with prompt length.** Even when content fits, prefilling 100K tokens of mostly-irrelevant context takes seconds and competes with every other request on the GPU. Retrieval cuts the prefill bill.
3. **Long-context quality degrades.** Models exhibit "lost-in-the-middle": attention concentrates on prompt extremes (start and end), and information in the middle gets less weight. Stuffing more context doesn't linearly improve answers.
4. **Cost amortization.** Embeddings of static content are computed once per ingestion. Querying the LLM over the full corpus would re-pay that cost on every query.

Retrieval is a cache for embedding work. The vector DB is its index.

## Practical heuristics

- **Whenever you reach for an LLM for "find / search / lookup / compare" tasks**, the right shape is *embedding model + vector DB* first, generative LLM only for the final synthesis (and often not even that).
- **Don't run a generative LLM where an embedding model would do.** Asking a 35B model "are these two strings similar?" is wasteful — score their embeddings' cosine distance instead.
- **Chunk size matters.** Too-large chunks dilute embedding signal (many topics in one vector). Too-small chunks lose context. ~256–512 tokens is a typical starting point; tune by retrieval quality.
- **Embedding models are small and warm-friendly.** They're prime candidates to keep loaded on a shared GPU since they serve a high request rate per GB of VRAM.

## Related Concepts

- [[llm/inference-prefill-and-decode]] — embedding models are essentially "prefill only" — they skip the expensive decode loop entirely.
- [[llm/sampling-knobs]] — none of these apply to embedding models; they have no sampler.
- [[llm/serving-runtime-and-vram]] — embedding models often sit on the same GPU as small generative models, sharing VRAM under the same multi-tenancy rules.
- [[llm/kv-cache]] — embedding models compute K, V (and Q) inside a single pass but don't grow a per-request cache the way decode does.
