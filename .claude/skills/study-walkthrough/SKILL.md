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

**At any point** during the session, the developer can say "show in Obsidian" to launch Obsidian and view wiki pages. Follow the "Show in Obsidian" flow in the wiki-write-protocol.

## Session Rules

For additional shared interactive principles (scope, handling disagreement, non-interactive mode), see `~/.claude/skills/references/interactive-principles.md`.

- ONE concept per message, under 150-200 words of prose. Pause for discussion.
- Start each phase with `Phase X/4: <title>`.
- Pause after each phase -- ask whether to continue or discuss. Never auto-advance.
- If the developer says "skip" or "I know this," fast-forward immediately.
- If the developer fails a recall question, do NOT skip -- walk through it again until internalized.
- **Read silently, never cat.** Run `scripts/wiki-search`, `scripts/wiki-due`, `scripts/wiki-probes`, `Read` of wiki/index/log files, and `mcp__flashcard-mcp__*` calls without preamble narration and without echoing their stdout, JSON, or file contents into chat. The chat shows only synthesized output — the calibration question, the gap surfaced, the next phase prompt. See AGENTS.md "Skill Design Principles → Read silently, never cat."

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

The walkthrough must not rely solely on model-internal knowledge. At Phase 1 Step 1, spawn a **background research subagent** (`run_in_background: true`) in parallel with the wiki/index lookups. It fetches authoritative sources (official docs, RFCs, source code, canonical references) and returns structured findings the main thread uses to ground Phase 2 explanations and Phase 4 wiki references.

**Subagent prompt (general topic):**

> Research `<topic>` for a developer walkthrough. Find 2-4 authoritative sources — prefer official docs, RFCs, source code, or canonical references over blog posts. Use `WebSearch` to locate them, `WebFetch` to read the most authoritative one or two. Return:
> 1. **Sources** — URL + one-line "what this is" for each (max 4)
> 2. **Load-bearing facts** — 3-6 facts the walkthrough should anchor on, each tagged with which source supports it
> 3. **Misconceptions / version gotchas** — anywhere common explanations diverge from the canonical source, or where behavior differs across versions
> 4. **Confidence** — `high` (multiple sources agree), `medium` (one authoritative source), `low` (sparse coverage — walk carefully)
>
> Under 400 words. No prose preamble, just the four sections.

**Variants:**

- `--from <url>` or pasted text: include the source in the prompt and ask the subagent to **cross-check** that source's claims against 1-2 other authoritative references. Flag any divergence.
- Refresh cadence on `depth >= 3` pages: narrow the prompt to "verify this page's load-bearing claims are still current; flag deprecations or version drift since `last_deepened`."
- Concise cadence: still run, but the result only needs to confirm-or-correct the one-pass restatement.

**Using the findings:**

- **Phase 2 grounding:** lead each concept with the canonical framing from the sources. If a source contradicts what you would have said from memory, use the source phrasing and surface the divergence inline ("the spec actually says X, not Y as I'd have guessed — here's why that matters"). When the developer's prediction is wrong, cite the source URL in the correction so they have somewhere to look further.
- **Phase 4 wiki write:** add a `## References` section listing the authoritative URLs (max 4) with one-line descriptions. Inline-link specific claims (`[per the RFC](url)`) when the claim is version-specific or non-obvious.
- **Confidence handling:** `low` confidence means push extra probes in Phase 2 and add a `> [Note] Sources sparse — verify before relying on this page` callout in Phase 4.

**Silent execution.** The subagent runs in the background — do not narrate "spawning research subagent" or echo its output. When it returns, fold the findings into the next phase message. If it errors or times out, note one line ("research unavailable — proceeding from model knowledge, flagged in Phase 4 references") and continue — do not block the developer.

**Skip research only when:** the topic is repository-internal (a codebase pattern, an internal script, a project decision) where no public authoritative source exists. Note the skip in the session log under a `Research:` field so the pattern is visible across sessions.

**Probes are exempt.** Research grounds *explanations*; probes ground via direct execution. When a probe is run (developer types a command, pastes the output), the probe output IS the authoritative source for that point — do not second-guess a probe with research, do not ask the developer to re-verify a probed result against docs, and do not require a probe-derived claim to carry a `## References` URL. If a probe contradicts the research findings, that's a finding worth surfacing ("the docs say X but your run shows Y — let's dig into why"), but the probe wins for the immediate question. Persisted probes under `probes/<topic-slug>/` are not subject to research-grounding either.

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

A separate axis from Mode Detection — sets *depth*, not *output type*. Default is **Learning**.

- **Learning** — predict-first mandatory on every concept, every concept gets an active challenge (the "Concrete example/challenge" bullet in Phase 2 is load-bearing here), loop on every failed recall. This is today's default behavior.
- **Refresh** — for high-depth pages (`depth >= 3`) or when the developer says "just refresh this." Probe only the `last_probed` queue, skip predictions on concepts calibrated as solid, no mandatory challenge on every concept — only on sections that were gap-flagged.
- **Concise** — single-pass re-read with one calibration check, no looping on failure. For when the developer just wants a compressed restatement. Session log coda collapses to one sentence.

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
   - `warn` / `pause` → full script output verbatim, then the gate question. Wait for an explicit answer before Phase 1.
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
5. **Spawn the research subagent in the background** per the "Research Grounding" section above. Do this at the same time as steps 1-4 — it should be running while calibration happens, so findings are ready by Phase 2. Skip only for repo-internal topics (note the skip in the session log).

**Step 2 -- Present existing knowledge:**

If wiki pages exist, check their `depth` and `last_deepened` frontmatter:
> You have a wiki page `[[architecture/event-sourcing]]` (depth: 2, last deepened 2026-03-15) covering: Core Concepts, Projections, Related Concepts.
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

**If recall had gaps -- fill them first:**
- Walk through the weak concepts again with fresh examples
- After each concept, ask the developer to explain it back
- If they fail -> drill deeper with simpler sub-concepts, then build back up
- Do NOT move on until the developer can articulate the concept clearly
- Only after gaps are filled, push into new territory

**If recall was poor -- start from foundations:**
- Walk through the core concepts as if teaching for the first time
- Build understanding incrementally: foundation -> mechanism -> application -> edge cases
- Frequent checks: "What would happen if...?" "Why does this matter?"

**Walkthrough techniques:**
- **Ground claims in research (probes exempt).** Lead each *explanatory* concept with the canonical framing from the Phase 1 research findings — not the model's first-pass paraphrase. When your memory phrasing diverges from the sources, use the source phrasing and surface the divergence ("I'd have said X, but the docs say Y — and that distinction matters because…"). Cite source URLs inline when a claim is version-specific or non-obvious. If the research subagent returned `low` confidence or hasn't returned yet by the time a load-bearing claim comes up, flag it in chat and push a probe instead of asserting. **Probes themselves are not grounded in research** — the probe's actual output is the ground truth for whatever it demonstrates. If a probe contradicts research, surface the contradiction but trust the probe for the immediate point.
- Show concrete codebase code, never abstract examples
- Ask predictions before revealing answers
- **Probe when possible.** For code-shaped concepts (git, Python, shell, SQL, API behavior, algorithms), ask the developer to actually run a minimal snippet and paste the output — `uv run python -c`, a repl one-liner, a `git` command, `curl | jq`, a unit test. Compare the output against the prediction they made in the concrete challenge step. Probes turn Assumed understanding into Known and catch the "I thought I knew this" failure mode that pure discussion misses. Skip probes for theory-only concepts where no small snippet would demonstrate the point.
- **Persist load-bearing probes.** When a probe changes the developer's understanding (prediction wrong, output surprising, or the probe resolved a gap that was gating the session), save it to `probes/<topic-slug>/YYYY-MM-DD-HHMM-<brief>.md` using the four-section format in `probes/README.md` (Prediction / Command / Output / Takeaway). Copy `probes/_template.md` to scaffold. Mirror the Takeaway into the session log's `Surprising:` or `Heuristic:` field so it's findable without grepping. Skip persistence for probes that merely confirmed what the developer already knew — those are ceremony. Before starting a walkthrough on a recurring topic, read existing probes under `probes/<topic-slug>/` so the session builds on them instead of relitigating.
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
2. **If any question fails**: Walk through that specific concept again -- do not skip
3. **Repeat until all questions are answered correctly**
4. **Identify remaining gaps**: "We covered X, Y, Z today. What still feels unclear?"

This is the key differentiator -- the skill loops on failure until concepts are internalized.

**Write-focused addition**: In write-focused mode, also ask the developer to confirm:
1. The key problem or context the page will cover
2. One concrete code example and why it works that way
3. Any gotchas or non-obvious behavior

If any of these are missing or vague, return to the relevant concept and discuss until the developer can articulate it.

### Phase 4/4: Write & Chain

**Before drafting anything**, internalize the prose conventions from `references/wiki-write-protocol.md` "Writing Style" section. The two highest-cost-to-fix-after-the-fact rules:

1. **No em-dashes** anywhere — not in prose, not in headings, not in link text, not in list-item descriptions, not in table cells. Use period, comma, parentheses, or `: ` after a wikilink/markdown-link/bold-term/code in list items.
2. **No prose-colons** as clause connectors. `The trap: in one document...` is flagged. Split into two sentences (`The trap. In one document...`) or rephrase.

A single page with 15+ em-dashes and 3+ prose-colons forces a multi-pass cleanup touching every line — write clean from the first draft.

**Filename = slugified title** (lint error, not warning). When the folder name disambiguates (e.g., `wiki/json-api/`), the title does not need to repeat the topic — `Document structure` is a cleaner title than `JSON:API document structure` because its slug equals the filename `document-structure.md`. Pick the filename first, then choose a title that slugifies back to it.

**Write-focused mode** -- proceed directly to wiki write:

1. **Present a brief outline first:** title, proposed H2 sections with a one-line description each. Wait for the developer to confirm or adjust before writing the full draft. Then start writing from the top.
2. Present the full draft wiki page with frontmatter, wikilinks, and all sections
2. For each section: ask the developer to explain it in their own words. If they cannot, discuss until they can.
3. Adjust the page based on gaps surfaced during review
4. **Probe sections:** Default `probe_sections` to all H2 headings except `Related Concepts`, `References`, `See also`, and `TL;DR`. Offer the developer a chance to mark any remaining sections as reference-only — but default-all is usually correct. Write `probe_sections` in frontmatter and seed `last_probed` with the same list (keeps the queue invariant `set(last_probed) == set(probe_sections)` true from day one; first review rotates as if fresh). **Heading quality gate:** before finalizing probe_sections, check each heading — if it doesn't tell you what to recall without re-reading the section, rename it first. `## Gotchas` is a weak prompt; `## nil on no match and chaining behavior` is a strong one.
5. Follow `references/wiki-write-protocol.md` for the full write flow
6. Log the session

**Deepen-focused mode** -- offer choices:

1. **"add flashcard"** -- Chain to `/study-flashcard` for concepts that need SRS reinforcement, especially the ones that were initially failed during calibration

2. **"write wiki"** -- Follow `references/wiki-write-protocol.md`. (Preflight was already run up front — no re-run needed.)
   - **Before drafting:** present a brief outline of what the page will cover — title, proposed H2 sections, one-line description of each section. Wait for the developer to confirm or adjust before writing the full draft. This is the wiki entry preview; start writing from the top only after the outline is approved.
   - If extending an existing page: add new sections for the deeper material, increment `depth` frontmatter (e.g., depth 1 -> 2), set `last_deepened` to today. If any new H2 sections were added, extend `probe_sections` to include them (excluding `Related Concepts`, `References`, `See also`, `TL;DR`) **and reset `last_probed` to match the new `probe_sections`** so the queue invariant holds (avoids a persistent `probe-rotation-drift` lint error between now and the next review).
   - If creating new: draft a full page with `depth: 1` and everything covered. Set `probe_sections` to all H2s except the reference-only set; seed `last_probed` with the same list.
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
- **Always include: `## References`** with up to 4 authoritative URLs from the Phase 1 research findings (one-line "what this is" per URL). Inline-link specific claims in the body (`[per RFC 6797 §7.2](url)`) when the claim is version-specific, contested, or non-obvious. If research was skipped (repo-internal topic) or unavailable, write `## References\n\n_None — repo-internal topic._` or `_Research unavailable at write time; verify before relying on this page._` so the gap is visible.
  - **`References` MUST NOT appear in `probe_sections` or `last_probed`.** It's a citation list, not study material — the probe-section default already excludes `Related Concepts`, `References`, `See also`, `TL;DR`. When extending an existing page with new H2s, include new study-worthy headings only — never add `References` to the queue.

**Session log** -- always append to `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder):

```markdown
## Session N -- Walkthrough (HH:MM)
- **Topic:** event sourcing
- **Mode:** write-focused | deepen-focused
- **Cadence:** learning | refresh | concise
- **Starting level:** partial recall (Core Concepts solid, Projections weak)
- **Covered:** event versioning, upcasting, schema evolution
- **Gaps filled:** projections (re-walked, now solid)
- **Wiki updates:** [[architecture/event-sourcing]] extended with 2 new sections (depth: 2 -> 3)
- **Flashcards:** 2 created for event versioning
- **Research:** 3 sources fetched (Greg Young's CQRS doc, EventStore docs, Martin Fowler's bliki) — confidence: high. Cited 2 inline in wiki page.
- **Surprising:** upcasting was expected to be a compile-time transform; it's runtime-per-event
- **Heuristic:** any change to a persisted event shape needs an upcaster, not a migration
- **Next-time unblocker:** a small probe script that replays one serialized event through the upcaster chain
```

**Look-Back fields are mandatory in Learning cadence, recommended in Refresh, and collapse to a single **Takeaway:** line in Concise.** If nothing was surprising, write `Surprising: none — cadence may have been too shallow` so the pattern shows up across sessions. The heuristic is the single line a future session in this area should read first.

## Wiki Page Structure (for new pages)

### 1. Frontmatter (YAML)
Required fields: `title`, `aliases`, `tags`, `created`, `updated`, `source_skill`
Optional: `flashcard_ids`, `depth`, `last_deepened`, `next_review`, `review_interval`

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

### 6. References (H2)
- Authoritative URLs (max 4) from Phase 1 research, each with a one-line "what this is"
- Prefer official docs, RFCs, source code, canonical references over blog posts
- Inline-link specific version-specific or non-obvious claims in the body in addition to listing here

### 7. Warnings/Notes
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
- Check wiki and flashcards before starting -- never start blind
- **Spawn the research subagent at Phase 1** for any externally-knowable topic — explanations must be grounded in authoritative sources, not just model memory. Probes are the exception: they ground themselves via execution.
- Calibrate before teaching -- never assume the developer's level
- Loop on failed recall -- never skip past a gap
- Use concrete codebase code, not abstract examples
- Log every session, even if no wiki write happens
- Track which concepts are new vs. reinforced for accurate logging

**Never:**
- Skip calibration when existing material exists
- Walk through an externally-knowable topic on model memory alone — research first, probe second, model paraphrase last
- "Verify" a probe-derived result with research — the probe is the ground truth for what it demonstrates
- Move past a concept the developer can't explain back
- Dump information without checking understanding
- Auto-write to wiki without developer requesting it (deepen-focused mode)
- Create flashcards automatically -- always offer, never force

## Developer Preference — Intuition First, Syntax as Reference

The developer wants walkthroughs and wiki pages centered on **high-level intuition and evaluation capacity** — tradeoffs, design principles, mental models, "when/why X over Y," threat models, failure modes, and concepts portable across languages/frameworks.

Syntax details (exact API signatures, flag defaults, enum values) **are welcome in walkthroughs and wiki pages** — they make the reference material useful. Lead with the intuition, include the syntax as supporting reference.

**Hard rule for the flashcard handoff:** if this session chains into `/study-flashcard`, do NOT propose syntax-recall cards. Only concept/tradeoff/intuition cards make it into the SRS. Syntax stays on the wiki page as a lookup.
