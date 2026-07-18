---
name: study-walkthrough
description: "Interactive walkthrough that calibrates to the developer's understanding, fills gaps, pushes deeper, and optionally writes wiki pages. Handles both new-topic documentation and progressive deepening of existing material. Trigger keywords: deepen, walkthrough, study deeper, revisit, create reference, document this pattern."
user_invocable: true
---

# /study-walkthrough — Interactive Walkthrough & Wiki Writing

Interactive walkthrough that builds on what the developer already knows. Checks existing wiki pages and flashcards, calibrates depth, fills gaps, and pushes into new territory. Each session on the same topic goes deeper. Optionally produces a wiki page as an artifact.

**Core guarantee:** The developer finishes with a deeper understanding than they started with. If they fail at specific questions, the skill walks through that concept again until it's internalized. Wiki pages grow as understanding grows.

## Wiki Integration

This skill reads from and writes to the developer wiki at `wiki/`. See `references/wiki-write-protocol.md` for the full "write wiki" flow, linking rules, and frontmatter spec.

**At any point** during the session, the developer can say "show in browser" to open wiki pages in the wiki-viewer app. Follow the "Show in browser" flow in the wiki-write-protocol.

## Session Rules

For additional shared interactive principles (scope, handling disagreement, non-interactive mode), see `~/.claude/skills/references/interactive-principles.md`.

- ONE concept per message, under 150-200 words of prose. Pause for discussion.
- Start each phase with `Phase X/4: <title>`.
- Pause after each phase -- ask whether to continue or discuss. Never auto-advance.
- If the developer says "skip" or "I know this," fast-forward immediately.
- If the developer fails a recall question, do NOT skip -- walk through it again until internalized.
- **Read silently, never cat.** Run `scripts/wiki-search`, `scripts/wiki-due`, `Read` of wiki/index/log files, and `mcp__flashcard-mcp__*` calls without preamble narration and without echoing their stdout, JSON, or file contents into chat. The chat shows only synthesized output — the calibration question, the gap surfaced, the next phase prompt. See AGENTS.md "Skill Design Principles → Read silently, never cat."

## Socratic Never-Reveal — The Developer Produces Every Answer (always on; not a selectable mode; overrides every reveal-style step below)

The interactive walkthrough never hands the developer a correct answer. The developer must produce every conclusion themselves; your job is to ask the next small question, not to state the next fact. When any step below says "explain", "walk through", "lead with the framing", or "reveal" — read it through this rule.

- **One small question at a time.** Decompose the concept into the smallest step the developer can reason about. Ask, wait, then react to their answer with the next question. Short steps, not lectures.
- **Never state the answer to fill a gap.** When the developer is wrong or blank, do NOT correct by asserting the right answer. Decompose further — ask an easier sub-question, point at a concrete value/snippet/error and ask what it implies, or narrow scope until they can take the next step. Hints get progressively more concrete, but the final words are always theirs. (This is the agreed stuck-fallback: decompose, never reveal.)
- **"Make it concrete" / "I don't understand" is NOT a reveal request.** When the developer says the *question* is unclear or asks you to make it concrete, make the **next question** smaller and more grounded (a specific value, a one-line snippet, a named scenario) — do **not** answer it for them or work the example to its conclusion. Reformulating the prompt is not the same as supplying the missing piece; a clarification plea answered with the full worked solution is the most common way revealing sneaks in.
- **Confirming is allowed; pre-empting is not.** Once the developer produces a correct answer, you may confirm it ("yes — that's it"). You may not say it first.
- **Applies to every cadence** (Learning, Refresh, Concise). Cadence sets how many questions and whether you loop on a miss — never whether you reveal.
- **The written wiki page is exempt.** Never-reveal governs the spoken dialogue. The Phase 4 wiki page is the reference artifact and naturally contains the facts — that is the payoff for reconstructing them in dialogue, not a shortcut around it.
- **Explicit request override.** The rule forbids *volunteering* the answer. If the developer explicitly asks ("just tell me", "show me the answer"), honor it — the human drives — then re-probe what you told them.
- **Research and codebase reads inform your questions, not your statements.** Use them so you know the right answer yourself (to judge theirs and craft the next question) and to source the written page — never as a script to read facts aloud.

## Running Ledger

For walkthroughs that span more than ~3 phase messages, maintain a tiny ledger at the top of each phase message (one line per field, skip empty fields):

- **Known:** concepts calibrated solid or probed successfully this session
- **Gaps filled:** concepts initially weak that were walked through and reconfirmed
- **Still fuzzy:** concepts flagged but not yet reinforced — these gate Phase 3 completion
- **Queued:** flashcard / wiki deltas to propose at Phase 4

The ledger is chat-only — do NOT write it into the wiki page. It exists so the developer (and you) can see session state at a glance and so Phase 3 verification targets the real gaps instead of a generic recall quiz. Skip the ledger for short walkthroughs (single-concept refreshes).

## Output Contract -- Progress Footer (mandatory)

Every assistant message in this skill **must end with a progress footer as the LAST line**. No exceptions while the interactive flow is active -- this includes clarifying questions, short acknowledgements, and messages that contain only code. A message without this footer is a contract violation.

**Format:**
- With steps: `Step 1/2 · Phase 2/4 — Adaptive Walkthrough: recall check`
- Without steps: `Phase 1/4 — Discovery & Calibration`

The footer is a single line, rendered verbatim, at the very bottom of the message -- nothing after it.

**Exceptions:** Omit the footer only when the developer has explicitly opted out of the interactive flow -- non-interactive subagent mode, or an explicit "one-shot explanation" request.

## MCP Server Dependency

This skill uses the `flashcard-mcp` MCP server for flashcard lookup. Tools used: `find_similar_cards`, `search_cards`, `get_card`.

## Research Grounding

The walkthrough must not rely solely on model-internal knowledge. At Phase 1 Step 1, run the **`research-grounding` workflow** (`.claude/workflows/research-grounding.js`) in the background, in parallel with the wiki/index lookups. It fans out across two lanes and synthesises one structured result the main thread uses to ground Phase 2 questions and the Phase 4 wiki page.

**Two lanes — and they are not equal:**

- **Authoritative lane (ground truth).** Official docs, specs, RFCs, source code, canonical references. This lane decides what is *factually true*. Every fact must be traceable to an authoritative source.
- **Practitioner lane (opinion).** Blog posts, conference talks, credible practitioner write-ups, high-signal forum threads. This lane adds what the docs leave out: tradeoffs, lived experience, architectural nuance, established-pattern critiques, and gotchas. It is **explicitly not ground truth** — every item stays labelled as opinion, attributed to its source, and marked `consensus` / `contested` / `single-voice`.

**The hard rule: authoritative wins for facts.** The synthesis step reconciles the two lanes and flags any practitioner claim that contradicts an authoritative fact (`contradictsGroundTruth: true`) — the fact stands, the blog claim is marked likely stale, wrong, or context-specific. An opinion is never promoted into a fact. Practitioner divergence (where blogs disagree with each other) is surfaced so the walkthrough can present it as genuinely open rather than settled.

**Invoking the workflow.** Call the `Workflow` tool with `name: "research-grounding"` and `args` as a **real JSON object — never a JSON-encoded string**. Pass the topic in full: `args: { "topic": "<the developer's full topic, verbatim>", "cadence": "learning" }`. Stringifying `args` (passing `"{\"topic\": ...}"`) is a known footgun — the workflow then sees no topic and the run is wasted; the workflow now rejects that case loudly, but get the call shape right the first time. This skill instructing you to call it IS the opt-in — no separate confirmation needed. Workflows run in the background automatically: the call returns a task id immediately and a notification arrives when synthesis completes, so kick it off at Phase 1 Step 1 and keep running calibration meanwhile (the developer is busy answering calibration questions while it works — same anti-slot-machine posture as the old single subagent). Pass args:

| arg | value |
| --- | --- |
| `topic` | the walkthrough topic |
| `cadence` | `learning` \| `refresh` \| `concise` — trims the fan-out (`concise`/`refresh` → 1+1, `learning` → 2+2 authoritative+practitioner agents) |
| `thoroughness` | optional `lite` \| `normal` \| `deep` — pass `deep` (3+3) for architecture/pattern topics where practitioner opinion matters most |
| `lastDeepened` | the existing page's `last_deepened`, if any (drives refresh narrowing) |
| `fromUrl` | the URL (or a note that source text was pasted) for `--from` / pasted-text invocations |

The workflow returns `{ confidence, authoritativeSources[], practitionerSources[], facts[], loadBearing[], misconceptions[], opinions[], divergence[] }` — where each opinion carries `{ claim, kind, source, stance, contradictsGroundTruth, note? }`.

**Variants (set via args):**

- `--from <url>` or pasted text: pass `fromUrl`. The authoritative lane cross-checks that source's factual claims against other authoritative references; the practitioner lane treats it as one opinion among several.
- Refresh cadence on previously-deepened pages (those with a `last_deepened` date): pass `lastDeepened`. Both lanes narrow to "what changed since then" — deprecations, version drift, and any newer practitioner consensus.
- Concise cadence: pass `cadence: "concise"`. Fan-out drops to 1+1; the result only needs to confirm-or-correct the one-pass restatement.

**Using the findings:**

- **Phase 2 grounding (facts).** `facts` / `loadBearing` equip *you* with the canonical answer so you can craft precise questions and judge the developer's answers — never read aloud (see Socratic Never-Reveal). If a source contradicts what you'd have said from memory, that sharpens the question you ask, not a spoken correction. When the developer's prediction is wrong, do not state the right answer; ask a smaller question that exposes the gap, and you may point them at the source URL to investigate themselves.
- **Phase 2 grounding (opinions).** `opinions` and `divergence` unlock a class of question the docs cannot ground: tradeoff and judgement prompts. Pose them as open ("practitioners disagree about X — what do you think the tradeoff is?", "here's a gotcha someone hit in production — why might that happen?"). Never present an opinion as settled fact, and never reveal — the opinion shapes the *question*, the developer still produces the answer. An opinion flagged `contradictsGroundTruth` is not used to question at all; the authoritative fact it contradicts is.
- **Phase 4 wiki write.** Fold facts and opinions into the page per the `## References` and `## Tradeoffs & gotchas` rules in "Wiki Page Structure" below: facts go to an authoritative `## References` (inline-link version-specific claims); load-bearing opinions go to a `## Tradeoffs & gotchas` H2 or inline `> [Note]` callouts, attributed and marked consensus/contested; drop any `contradictsGroundTruth` opinion.
- **Confidence handling:** `confidence: low` means push extra probes in Phase 2 and add a `> [Note] Sources sparse. Verify before relying on this page.` callout in Phase 4. A `contested` opinion stance means present both sides; do not declare a winner the sources do not support.

**Silent execution.** The workflow runs in the background — do not narrate "running research workflow", echo its `/workflows` progress tree, or paste its output. When the synthesis notification arrives, fold the findings into the next phase message. If the workflow errors or times out, fall back to a single background research subagent using the two-lane fallback prompt below; if that also fails, note one line ("research unavailable — proceeding from model knowledge, flagged in Phase 4 references") and continue — never block the developer.

**Single-agent fallback prompt** (only when the workflow itself cannot run):

> Research `<topic>` for a developer walkthrough across two lanes, kept separate. **Authoritative (ground truth):** find 2-3 official docs / RFCs / source / canonical refs (`WebSearch` then `WebFetch`); return load-bearing facts, each tagged with its source and confidence. **Practitioner (opinion):** find 1-2 credible blog posts / talks / forum threads; return tradeoffs, experiences, architectural nuances, and gotchas, each tagged with its source and stance (consensus | contested | single-voice). Then reconcile: authoritative wins for any factual conflict — flag practitioner claims that contradict a fact as likely stale/wrong, never promote an opinion to a fact. Return `confidence` (high|medium|low), the authoritative facts, the labelled opinions, misconceptions/version gotchas, and any practitioner divergence. Under 450 words, no preamble.

**Skip research only when:** the topic is repository-internal (a codebase pattern, an internal script, a project decision) where no public authoritative source exists. Note the skip in the session log under a `Research:` field so the pattern is visible across sessions.

**Probes are exempt.** Research grounds *explanations*; probes ground via direct execution. When a probe is run (developer types a command, pastes the output), the probe output IS the authoritative source for that point — do not second-guess a probe with research, do not ask the developer to re-verify a probed result against docs, and do not require a probe-derived claim to carry a `## References` URL. If a probe contradicts the research findings, that's a finding worth surfacing ("the docs say X but your run shows Y — let's dig into why"), but the probe wins for the immediate question.

## Invocation

```
/study-walkthrough                        — Start (asks for topic)
/study-walkthrough <topic>                — Walkthrough on a specific topic
/study-walkthrough --write <topic>        — Write-focused: walkthrough → wiki page (always writes)
/study-walkthrough --from <url>           — Walkthrough from URL content
/study-walkthrough <pasted text>          — Walkthrough from provided text
```

When invoked with `--write`, the session defaults to producing a wiki page as the primary artifact. The walkthrough still ensures understanding, but Phase 4 writes to wiki by default rather than offering it as an option.

When invoked with a URL or pasted text, use it as source material. The walkthrough and wiki page capture only what the developer actually understood -- not a raw dump.

## Mode Detection

The skill operates in two modes based on invocation and context:

- **Write-focused**: Triggered by `--write` flag, `--from <url>`, or pasted source text. Also triggered when no existing wiki material is found and the developer's intent is clearly "document this." Compresses calibration, writes wiki by default at the end.
- **Deepen-focused**: Default mode. Full calibration against existing material, adaptive depth, wiki write offered but not assumed.

## Session Cadence

A separate axis from Mode Detection — sets *depth*, not *output type*. Default is **Learning**. **All three cadences are question-driven and never reveal the answer** (see Socratic Never-Reveal); cadence only sets how many questions and whether you loop on a miss.

- **Learning** — predict-first mandatory on every concept, every concept gets an active challenge (the "Concrete example/challenge" bullet in Phase 2 is load-bearing here), loop on every failed recall (decompose into smaller questions, never reveal). This is today's default behavior.
- **Refresh** — for previously-deepened pages (those with a `last_deepened` date) or when the developer says "just refresh this." Question only the `last_probed` queue, skip predictions on concepts calibrated as solid, no mandatory challenge on every concept — only on sections that were gap-flagged. Still never reveals.
- **Concise** — a fast question-driven pass with one calibration check, no looping on a miss. For when the developer wants speed: fewer questions, and you move on rather than decomposing when they miss — but you still never hand them the answer. Session log coda collapses to one sentence.

Announce the active cadence in Phase 1 Step 3 after calibration. If calibration reveals a mismatch (developer keeps saying "I know this" → bump to Refresh; keeps saying "wait, walk me through that again" → bump to Learning), suggest a cadence change once. Do not switch silently.

## Correction Primitive

When the developer corrects something you said in a prior phase:

- **Edit the original statement in place** — in the chat summary and in any in-progress wiki draft. Do not append "actually, X" at the bottom.
- If the correction invalidates a drafted flashcard or wiki section, mark it `[STALE — redraw]` and redo it together before advancing.
- In chat, acknowledge the edit with one line: "Updated Phase 2 — the explanation of X now reads Y." Then continue from the corrected state.
- Never carry forward a concept the developer flagged as wrong.

This matters because the walkthrough compounds: a wrong explanation in Phase 2 poisons the recall check in Phase 3 and the wiki draft in Phase 4.

## Preflight — SRS Pressure Check (MANDATORY, ALWAYS FIRST)

**Before Phase 1. Before any tool call. Before any wiki-index read, TreeSearch, wiki-search, `find_similar_cards`, or drafting.** The first assistant message of this skill invocation must be the pressure-check output — nothing else. This applies regardless of mode, flags, or whether a wiki page will be written.

Follow `references/srs-pressure-check.md` exactly. Summary:

1. Run `scripts/srs-pressure --human` — it fetches accurate counts via the flashcard-mcp CLI itself. Do **not** call `mcp__flashcard-mcp__get_due_cards` or `mcp__flashcard-mcp__list_decks` for pressure signals (`get_due_cards` caps at 30 and will underreport).
2. First message output:
   - `ok` → one line: `SRS pressure: ok — proceeding.`
   - `warn` / `pause` → full script output verbatim, then the gate question. Wait for an explicit answer before Phase 1. **Exception:** if `--no-study` was already specified at invocation, skip the gate question — one status line, then proceed straight to Phase 1 (see `references/srs-pressure-check.md`).
3. Progress footer for this message: `Preflight — SRS Pressure Check`.

**Contract:** skipping this step, folding it into Phase 1, or running other tool calls before the verdict is a contract violation — same severity as omitting the progress footer. The developer can always opt out of downstream steps (e.g., "just deepen, no wiki") mid-session — that does not justify skipping preflight.

## Phase Flow

### Phase 1/4: Discovery & Calibration

(Preflight must be complete and — if warn/pause — explicitly acknowledged by the developer before starting this phase.)

**Step 1 -- Find what exists (and start research in parallel):**

1. Read `wiki/.wiki-index.json` for the topic
2. Run `treesearch search --query "<topic>" --index_dir wiki/indexes` for keyword matches
3. Run `scripts/wiki-search "<topic>"` for semantic matches (if Ollama running)
4. Call `find_similar_cards` from MCP to find related flashcards
5. **Run the `research-grounding` workflow in the background** per the "Research Grounding" section above (passing `topic`, `cadence`, and — if a page exists — `lastDeepened`). Do this at the same time as steps 1-4 — it should be running while calibration happens, so the synthesised two-lane findings are ready by Phase 2. Skip only for repo-internal topics (note the skip in the session log).

**Step 2 -- Present existing knowledge:**

If wiki pages exist, check their `last_deepened` frontmatter:
> You have a wiki page `[[architecture/event-sourcing]]` (last deepened 2026-03-15) covering: Core Concepts, Projections, Related Concepts.
> You also have 4 flashcards on this topic.
> Let me check what you actually remember.

If no wiki pages exist:
> No wiki pages found for this topic. Let's build your understanding from scratch.

**Step 3 -- Calibration:**

- **If existing material found**: Ask 1-2 targeted recall questions drawn from existing wiki page content (key concepts from sections) and flashcard backs (pick the hardest ones).
- **If no existing material (write-focused)**: Ask one question: "What do you already know about this topic?" This sets the depth for Phase 2 without a full calibration cycle.
- **If no existing material (deepen-focused)**: Same single question, then proceed to full walkthrough.

Evaluate the developer's answers:
- **Solid recall** -> "Good -- you've internalized the basics. Let's go deeper into [new area]."
- **Partial recall** -> "You remember the gist but some details are fuzzy. Let me walk through the gaps."
- **Poor recall** -> "Let's revisit the fundamentals before going deeper."

This calibration determines where Phase 2 starts.

**Step 4 -- Scope & page type (write-focused mode only):**

If the session is write-focused, decide scope and page type now:

- **Scope decision tree:**
  - If the topic decomposes into >5 sub-concepts: suggest splitting into multiple pages
  - If the developer already knows the topic well: compress Phase 2 and move to drafting
  - If the topic is trivial (single fact or one-liner): suggest adding it to an existing page or skipping

- **Page type** (choose together):
  - **Tutorial/Concept** -- for learning a new pattern or technique
  - **Problem-Solution** -- for documenting a specific gotcha, failure mode, or fix
  - **Pattern/Technique** -- for documenting an established, repeatable approach
  - **Feature/Tool Overview** -- for documenting capabilities and API surface

### Phase 2/4: Adaptive Walkthrough

Based on calibration results, the walkthrough adapts:

**If recall was solid -- push deeper:**
- Identify areas the existing wiki page doesn't cover
- Explore edge cases, advanced patterns, real-world tradeoffs
- Use concrete codebase code to illustrate advanced concepts
- Ask the developer to predict behavior in complex scenarios

**If recall had gaps -- fill them first (via questions, never explanation):**
- Re-approach the weak concepts with fresh, concrete questions — do not re-explain them
- After each concept, ask the developer to articulate it back in their own words
- If they fail -> decompose into a smaller sub-question, then build back up. Never reveal the answer to fill the gap.
- Do NOT move on until the developer can articulate the concept clearly themselves
- Only after gaps are filled, push into new territory

**If recall was poor -- build from foundations (Socratically):**
- Lead the developer to the core concepts through a chain of small questions, as if drawing it out of them for the first time — not lecturing it
- Build understanding incrementally: foundation -> mechanism -> application -> edge cases, each step a question they answer
- Frequent checks: "What would happen if...?" "Why does this matter?" — and when they stall, a smaller question, never the answer

**Walkthrough techniques:**
- **Ground your questions in research (probes exempt).** Use the Phase 1 research findings so *you* hold the canonical answer — then ask the developer toward it; do not read the framing aloud (see Socratic Never-Reveal). When your memory diverges from the sources, the source wins for judging the developer's answer and for the written page. Cite source URLs only as a place for the developer to investigate, never as the answer itself. If the research grounding came back `low` confidence or hasn't returned by the time a load-bearing point comes up, push a probe instead of asserting. **Probes themselves are not grounded in research** — the probe's actual output is the ground truth for whatever it demonstrates. If a probe contradicts research, surface the contradiction but trust the probe for the immediate point.
- Show concrete codebase code, never abstract examples
- Ask a guiding question and wait — never reveal the answer. On a wrong or blank answer, decompose into a smaller sub-question rather than correcting by assertion.
- **Probe when possible.** For code-shaped concepts (git, Python, shell, SQL, API behavior, algorithms), ask the developer to actually run a minimal snippet and paste the output — `uv run python -c`, a repl one-liner, a `git` command, `curl | jq`, a unit test. Compare the output against the prediction they made in the concrete challenge step. Probes turn Assumed understanding into Known and catch the "I thought I knew this" failure mode that pure discussion misses. Skip probes for theory-only concepts where no small snippet would demonstrate the point.
- **Capture load-bearing probe takeaways.** When a probe changes the developer's understanding (prediction wrong, output surprising, or the probe resolved a gap that was gating the session), mirror the Takeaway (Prediction / Command / Output / Takeaway) into the session log's `Surprising:` or `Heuristic:` field so it's findable later. Skip capture for probes that merely confirmed what the developer already knew — those are ceremony.
- When the developer's explanation is incomplete, ask a follow-up rather than correcting
- **Concrete example/challenge (mandatory, every concept):** For each concept walked through, ask the developer to actively produce something -- not just passively receive:
  - **Code concepts:** "What do you expect this outputs?" / "How would you write the code for that?" / "Here's a broken version -- what's wrong?" -- show a snippet and require a prediction or solution
  - **Theory/architecture concepts:** "When would you choose this over X?" / "What breaks if you skip this step?" / "Explain why this matters in your own words"
  - Keep each challenge focused -- one question, not a quiz. The developer's answer reveals whether they truly internalized the concept or just followed along.
- Track related concepts for wiki linking as they come up
- Note which areas are new understanding (these become wiki page extensions)

### Phase 3/4: Verification & Gaps

After the walkthrough:

1. **Recall check**: Ask 2-3 questions covering both the new material AND the previously weak areas
2. **If any question fails**: re-approach that concept with smaller guiding questions until the developer gets there themselves -- never reveal, do not skip
3. **Repeat until all questions are answered correctly by the developer**
4. **Identify remaining gaps**: "We covered X, Y, Z today. What still feels unclear?"

This is the key differentiator -- the skill loops on failure until concepts are internalized.

**Write-focused addition**: In write-focused mode, also ask the developer to confirm:
1. The key problem or context the page will cover
2. One concrete code example and why it works that way
3. Any gotchas or non-obvious behavior

If any of these are missing or vague, return to the relevant concept and discuss until the developer can articulate it.

### Phase 4/4: Write & Chain

**Before drafting anything**, internalize the "Writing Style" section of `references/wiki-write-protocol.md`. The two costliest-to-fix-after-the-fact rules: **no em-dashes anywhere** (prose, headings, link text, list-item descriptions, table cells) and **no prose-colons as clause connectors** (`The trap: ...` is flagged — split into two sentences). A page with many of either forces a multi-pass cleanup touching every line; write clean from the first draft.

**Filename = slugified title** (lint error, not warning). When the folder name disambiguates (e.g., `wiki/json-api/`), the title does not need to repeat the topic — `Document structure` is a cleaner title than `JSON:API document structure` because its slug equals the filename `document-structure.md`. Pick the filename first, then choose a title that slugifies back to it.

**Write-focused mode** -- proceed directly to wiki write:

1. **Present a brief outline first:** title, proposed H2 sections with a one-line description each. Wait for the developer to confirm or adjust before writing the full draft. Then start writing from the top.
2. Present the full draft wiki page with frontmatter, wikilinks, and all sections
3. For each section: ask the developer to explain it in their own words. If they cannot, discuss until they can.
4. Adjust the page based on gaps surfaced during review
5. **Probe sections:** Default `probe_sections` to all H2 headings except `Related Concepts`, `References`, `See also`, and `TL;DR`. Offer the developer a chance to mark any remaining sections as reference-only — but default-all is usually correct. Write `probe_sections` in frontmatter and seed `last_probed` with the same list (keeps the queue invariant `set(last_probed) == set(probe_sections)` true from day one; first review rotates as if fresh). **Heading quality gate:** before finalizing probe_sections, check each heading — if it doesn't tell you what to recall without re-reading the section, rename it first. `## Gotchas` is a weak prompt; `## nil on no match and chaining behavior` is a strong one.
6. Follow `references/wiki-write-protocol.md` for the full write flow
7. Log the session

**Deepen-focused mode** -- offer choices:

1. **"add flashcard"** -- Chain to `/study-flashcard` for concepts that need SRS reinforcement, especially the ones that were initially failed during calibration

2. **"write wiki"** -- Follow `references/wiki-write-protocol.md`. (Preflight was already run up front — no re-run needed.)
   - **Before drafting:** present a brief outline of what the page will cover — title, proposed H2 sections, one-line description of each section. Wait for the developer to confirm or adjust before writing the full draft. This is the wiki entry preview; start writing from the top only after the outline is approved.
   - If extending an existing page: add new sections for the deeper material, set `last_deepened` to today. If any new H2 sections were added, extend `probe_sections` to include them (excluding `Related Concepts`, `References`, `See also`, `TL;DR`) **and reset `last_probed` to match the new `probe_sections`** so the queue invariant holds (avoids a persistent `probe-rotation-drift` lint error between now and the next review).
   - If creating new: draft a full page with everything covered. Set `probe_sections` to all H2s except the reference-only set; seed `last_probed` with the same list.
   - Include `flashcard_ids` for any related cards
   - Run `scripts/wiki-write`, append session log

3. **"done"** -- Just log the session, no writes

**Wiki write details (both modes):**

When writing a wiki page, follow this structure:

- If extending an existing page: read the existing file, add new H2 sections, preserve existing links
- If creating new, use the page type chosen in Phase 1 to determine structure:
  - **Tutorial/Concept**: `## TL;DR` with key takeaways, then H2 sections per concept
  - **Problem-Solution**: Brief context, then `## The problem` then `## How to fix it`
  - **Pattern/Technique**: Jump into the pattern with descriptive H2/H3 headings
  - **Feature/Tool Overview**: What is possible, then H2 sections per feature
- Always include: `## Related Concepts` with `[[absolute/path]]` wikilinks
- **Always include `## References`**, plus a `## Tradeoffs & gotchas` H2 (or inline `> [Note]` callouts) when practitioner opinion is load-bearing. Build both per "Wiki Page Structure" sections 6 & 7 below: facts cite the authoritative lane, opinions stay attributed and labelled consensus/contested, `contradictsGroundTruth` opinions are dropped, and `## References` never enters `probe_sections`.

**No-study capture (excluded from the study loop).** When the developer wants the topic in the wiki but **not** in the study loop — the `no-study` path chosen at the SRS pressure gate, or any "exclude from study loop" / "don't schedule it" / "just capture it, no review" at the walkthrough limit or later — write the page exactly as above (full content, `probe_sections`, links) but **add `no-study` to the frontmatter `tags`** (e.g. `tags: [security, no-study]`). Everything else is normal: `scripts/wiki-write` still fills `next_review`/`review_interval`, the page stays in the graph, search, and index, and it renders with a `not in study loop` marker; the `no-study` tag alone keeps it out of review and off the SRS pressure count. To toggle an existing page later, run `scripts/wiki-no-study <page>` (add `--include` to rejoin the study loop) rather than hand-editing the tag. See "Excluded from the study loop (`no-study`)" in `references/wiki-write-protocol.md`.

**Session log** -- always append to `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder):

```markdown
## Session N -- Walkthrough (HH:MM)
- **Topic:** event sourcing
- **Mode:** write-focused | deepen-focused
- **Cadence:** learning | refresh | concise
- **Starting level:** partial recall (Core Concepts solid, Projections weak)
- **Covered:** event versioning, upcasting, schema evolution
- **Gaps filled:** projections (re-walked, now solid)
- **Wiki updates:** [[architecture/event-sourcing]] extended with 2 new sections
- **Flashcards:** 2 created for event versioning
- **Research:** research-grounding workflow — 2 authoritative (Greg Young's CQRS doc, EventStore docs) + 2 practitioner (Martin Fowler's bliki, a production post-mortem); confidence: high. 1 blog claim flagged contradictsGroundTruth (dropped). Cited 2 authoritative inline; 1 tradeoff surfaced in `## Tradeoffs & gotchas`.
- **Surprising:** upcasting was expected to be a compile-time transform; it's runtime-per-event
- **Heuristic:** any change to a persisted event shape needs an upcaster, not a migration
- **Next-time unblocker:** a small probe script that replays one serialized event through the upcaster chain
```

**Look-Back fields are mandatory in Learning cadence, recommended in Refresh, and collapse to a single **Takeaway:** line in Concise.** If nothing was surprising, write `Surprising: none — cadence may have been too shallow` so the pattern shows up across sessions. The heuristic is the single line a future session in this area should read first.

## Wiki Page Structure (for new pages)

### 1. Frontmatter (YAML)
Required fields: `title`, `aliases`, `tags`, `created`, `updated`, `source_skill`
Optional: `flashcard_ids`, `last_deepened`, `next_review`, `review_interval`

### 2. Title (H1)
- Clear, descriptive title identifying the topic
- Use imperative form for how-to topics
- Use descriptive form for concept topics
- Prefix with "Careful:" or "Warning:" for gotcha-style pages

### 3. Opening Context (varies by page type)
Structure depends on the page type chosen in Phase 1.

### 4. Code Examples
- Minimal but complete enough to be functional
- Show bad examples with `# bad` comment, good with `# good` comment
- Use code from the actual codebase when possible

### 5. Related Concepts (H2)
- `[[absolute/path]]` wikilinks with brief relationship descriptions

### 6. Tradeoffs & gotchas (H2, optional — when practitioner opinion is load-bearing)
- Collects the workflow's practitioner `opinions`: tradeoffs, lived experience, architectural nuance, gotchas
- Each point attributed to its source and marked consensus/contested; framed as opinion, never as ground truth
- One-off nuances go inline as `> [Note]` callouts in the relevant section instead of here
- This H2 is study-worthy — include it in `probe_sections` (unlike `References`)
- Drop any opinion the workflow flagged `contradictsGroundTruth` — keep the authoritative fact it contradicts instead

### 7. References (H2)
- Authoritative URLs (max 4) from Phase 1 research, each with a one-line "what this is"
- Prefer official docs, RFCs, source code, canonical references for ground truth — facts cite this lane
- When practitioner sources were used, list them under a `**Practitioner / opinion:**` sub-label, distinct from the authoritative URLs. **A factual claim in the body must never be cited only to a practitioner source.**
- Inline-link specific version-specific, contested, or non-obvious claims in the body (`[per RFC 6797 §7.2](url)`) in addition to listing here
- **Never put `## References` in `probe_sections` / `last_probed`** — it's a citation list, not study material (the probe-section default already excludes it)
- If research was skipped (repo-internal topic) or unavailable, still write the section as `_None — repo-internal topic._` or `_Research unavailable at write time; verify before relying on this page._` so the gap is visible

### 8. Warnings/Notes
- Short warnings: bold inline. Standalone callouts: `> [Warning]` / `> [Note]`

## Writing Style

- Concise -- every sentence adds value
- Technically precise -- exact terms, versions, paths
- Practical -- working code, not pseudocode
- Insightful -- non-obvious information
- No emojis

## Chaining

**Into /study-walkthrough:**
- After `/study` reveals weak areas -> "You had 2 lapses on event sourcing. Let's deepen that."
- After `/study-flashcard` -> "Want to explore these concepts more deeply?"

**Out of /study-walkthrough:**
- After walkthrough -> offer `/study-flashcard` for SRS reinforcement
- After walkthrough -> offer `/study` to immediately review related cards

## Guardrails

**Always:**
- Fill every gap with a question, never an assertion (Socratic Never-Reveal) -- the developer produces every answer in the dialogue
- Check wiki and flashcards before starting -- never start blind
- **Run the `research-grounding` workflow at Phase 1** for any externally-knowable topic — explanations must be grounded in authoritative sources (facts) and enriched with practitioner opinion (tradeoffs, gotchas), not just model memory. Authoritative always wins for facts; opinions stay labelled and never override ground truth. Probes are the exception: they ground themselves via execution.
- Calibrate before teaching -- never assume the developer's level
- Loop on failed recall -- never skip past a gap
- Use concrete codebase code, not abstract examples
- Log every session, even if no wiki write happens
- Track which concepts are new vs. reinforced for accurate logging

**Never:**
- Reveal or state a correct answer to fill a gap in the dialogue -- decompose into a smaller question instead (explicit developer request and the written wiki page excepted)
- Skip calibration when existing material exists
- Walk through an externally-knowable topic on model memory alone — research first, probe second, model paraphrase last
- Present a practitioner opinion as ground truth, or cite a factual body claim only to a blog — facts come from the authoritative lane; opinions stay labelled and attributed
- Promote an opinion the workflow flagged `contradictsGroundTruth` — keep the authoritative fact it contradicts
- "Verify" a probe-derived result with research — the probe is the ground truth for what it demonstrates
- Move past a concept the developer can't explain back
- Dump information without checking understanding
- Auto-write to wiki without developer requesting it (deepen-focused mode)
- Create flashcards automatically -- always offer, never force

## Developer Preference — Intuition First, Syntax as Reference

The developer wants walkthroughs and wiki pages centered on **high-level intuition and evaluation capacity** — tradeoffs, design principles, mental models, "when/why X over Y," threat models, failure modes, and concepts portable across languages/frameworks.

Syntax details (exact API signatures, flag defaults, enum values) **are welcome in walkthroughs and wiki pages** — they make the reference material useful. Lead with the intuition, include the syntax as supporting reference.

**Hard rule for the flashcard handoff:** if this session chains into `/study-flashcard`, do NOT propose syntax-recall cards. Only concept/tradeoff/intuition cards make it into the SRS. Syntax stays on the wiki page as a lookup.
