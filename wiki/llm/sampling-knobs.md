---
title: Sampling Knobs
aliases:
- temperature num_predict think
- LLM API knobs
- thinking mode footgun
- LLM sampling controls
- temperature 0
tags:
- llm
- inference
- sampling
- ollama
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
depth: 1
probe_sections:
- The decode loop has a sampler
- Temperature - how peaked the distribution is
- num_predict - the output cap
- Thinking mode - reasoning preamble
- Choosing knobs by task shape
last_probed:
- The decode loop has a sampler
- Temperature - how peaked the distribution is
- num_predict - the output cap
- Thinking mode - reasoning preamble
- Choosing knobs by task shape
review_interval: 8
next_review: '2026-05-15'
flashcard_ids: []
---

# Sampling Knobs

## TL;DR

The decode loop produces a probability distribution over the next token at every step; a small **sampler** picks one. The three knobs that matter most in production. **`temperature`** controls how peaked the distribution is (0 = always pick the top token, deterministic; higher = more variety); **`num_predict`** caps output length and is the main circuit breaker against runaway generation; **`think`** toggles a hidden reasoning preamble that multiplies decode time and is a footgun when left at the default (`true` for models that support it). Pick knobs by *task shape*, not vibes. Extraction wants `temp 0`, never wants `think true`.

## The decode loop has a sampler

Every decode step (see [[llm/inference-prefill-and-decode]]) ends with the model producing a vector of raw scores ("logits"). One per token in the vocabulary, often ~150,000 entries. Those logits are turned into a probability distribution by softmax, and a sampler picks one token from that distribution. That picked token is then fed back as input for the next step.

The sampler is the main place where a deployment shapes model behavior at runtime. Most "production knobs" are sampler knobs.

## Temperature - how peaked the distribution is

Before softmax, the logits are divided by `temperature`:

```
probabilities = softmax(logits / temperature)
```

The effect on the distribution shape:

| `temperature` | Distribution behavior | Sampling result |
|---|---|---|
| `0` (degenerate case) | infinitely peaked on the top token | **argmax**. Always the highest-scoring token |
| `0.3` | sharply peaked on top tokens | top token usually wins; occasional drift to runners-up |
| `1.0` | the model's "natural" distribution | balanced sampling |
| `1.5+` | flattened distribution | low-probability tokens get a real chance. Creative, sometimes incoherent |

**Implementation note:** `temperature: 0` is typically implemented as "skip sampling, take the argmax". Division by zero is avoided with a special-case in the runtime.

### Use cases

- **`0`: structured extraction, classification, deterministic outputs.** JSON extraction, "is this email spam?", "extract the date from this paragraph." You want the same input to produce the same output every time.
- **`0.3`–`0.5`: lightly varied responses where strict determinism isn't required.** Q&A bots that should sound natural but stay grounded.
- **`0.7`–`1.0`: creative writing, brainstorming, generation tasks.** The same prompt twice should produce two different answers.
- **`>1.0`: rare, diagnostic or stylistic experiments.** Most production deployments stay at or below 1.

### Why temperature is dangerous for structured outputs

For free-form text, `temperature: 0.5` is fine. Readers don't notice an occasional unusual word. For JSON or structured output, even mild temperature is risky. The mechanism is this. At any decode step the sampler can pick a low-probability token. If that off-distribution pick lands inside structured syntax (e.g., a stray non-`}` token where the model was supposed to close an object), the model continues "in style" with the broken prefix and often spirals. Generating thousands of malformed tokens until it hits some natural stop or `num_predict`.

The fix is just `temperature: 0`. Argmax-only decoding can't make off-distribution leaps; the worst it can do is be wrong on a confident token, which is much rarer.

## num_predict - the output cap

`num_predict` (also called `max_tokens` in some APIs) is a hard upper bound on how many tokens decode produces in one request. When the limit is reached, decode stops regardless of what the model wanted to do next.

Decode time scales linearly with output length. Without `num_predict`, decode is bounded only by the model emitting a stop token (which relies on the model behaving sensibly) or the runtime's internal max (often the full context length minus prompt). Both are dangerous as the only ceiling. A model that drifts off-distribution (bad temperature, ambiguous prompt, looping behavior) can burn through thousands of tokens of nonsense before hitting either condition. **A 30-second hang on a request that should produce 200 tokens is the textbook symptom of missing `num_predict`.**

### Sizing num_predict

Pick the smallest value the use case can tolerate, with a comfortable margin. The cap is a safety net, not a target. The model rarely uses the full budget.

| Task | Suggested `num_predict` |
|---|---|
| Classification (single label) | 32–64 |
| Short JSON extraction | 256–512 |
| Long structured extraction | 512–1024 |
| Short summary | 256–512 |
| Long summary or article | 1024–4096 |
| Code generation | 1024–4096 |

**Rule:** if you have no idea, set 512 and tune up only if real responses get truncated.

## Thinking mode - reasoning preamble

Some recent models are trained to emit a hidden **reasoning preamble** before the actual answer. A stream of internal-monologue tokens (often wrapped in `<think>…</think>`) where the model works through the problem before producing user-visible output. The preamble is hidden from the user but **costs decode time exactly like normal output tokens.** Reasoning preambles can easily be 500–5,000 tokens.

The runtime exposes this as a `think` flag. **Ollama defaults `think: true`** for any model that supports it, which means a default-configured request can spend tens of seconds generating hidden tokens before the user sees anything.

### The "thinking equals more precise" trap

The intuitive read of "thinking mode" is "more thinking → better answers." This is **partly true and mostly misleading.**

Thinking mode helps when the task **genuinely requires multi-step reasoning over the answer**. Math word problems, code debugging, multi-hop logical inference, tasks where the model needs to enumerate cases or work through derivations. For those, the reasoning preamble does improve correctness.

For most production tasks (extraction, classification, format conversion, summarization, retrieval-augmented Q&A), thinking mode adds latency and **does not improve correctness.** It can even hurt. Longer preambles sometimes drift, and the model may rationalize a hallucinated answer rather than just emitting the right one.

**Practical rule:**

> Thinking helps when the task requires reasoning *over* the answer, not when it requires *producing* the answer.

| Task | `think` |
|---|---|
| JSON extraction from email | `false` |
| Classification | `false` |
| Format conversion | `false` |
| Summarization | `false` |
| RAG-grounded Q&A on simple facts | `false` |
| Math word problem | `true` (if latency budget allows) |
| Code debugging | `true` (if latency budget allows) |
| Multi-hop reasoning ("who was X's mother's employer?") | `true` |

**Always set `think` explicitly.** Defaulting to `true` is the footgun.

### When thinking is also wrong-shaped for the model

Thinking mode is most useful on small-to-medium models. They benefit most from "thinking it through." For very large models (100B+ parameters), thinking adds enormous latency without proportional accuracy gain, because the model is already strong enough to one-shot most tasks. Many shops set `think: false` as a hard rule on their largest model and only enable it for smaller ones with explicit need.

## Choosing knobs by task shape

A rough decision table for new features:

| Task type | `temperature` | `num_predict` | `think` |
|---|---|---|---|
| Structured extraction (JSON, fields) | `0` | small (256–1024) | `false` |
| Classification | `0` | very small (32–64) | `false` |
| Summarization (factual) | `0`–`0.3` | medium (512–2048) | `false` |
| Q&A over retrieved docs (RAG) | `0`–`0.3` | medium (512–1024) | `false` (usually) |
| Creative writing | `0.7`–`1.0` | task-shaped | `false` |
| Math / debug / multi-hop reasoning | `0`–`0.3` | large enough for the answer | `true` (if latency allows) |

If a feature has more than one task shape (e.g., extraction *and* a creative summary), split into two API calls with different knobs rather than picking one compromise setting.

## Related Concepts

- [[llm/inference-prefill-and-decode]]: the loop the sampler runs inside; explains why each token costs a forward pass and why output length dominates latency.
- [[llm/kv-cache]]: `num_predict` ultimately caps how far the per-request cache grows.
- [[llm/serving-runtime-and-vram]]: `think: true` worsens VRAM pressure indirectly: longer decode means a slot stays occupied longer, blocking other concurrent requests.
- [[llm/embeddings-vs-embedding-layer]]: embedding model calls don't have a sampler at all (no decode loop), so none of these knobs apply.
