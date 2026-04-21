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

## Invocation

```
/study-walkthrough                        — Start (asks for topic)
/study-walkthrough <topic>                — Walkthrough on a specific topic
/study-walkthrough --write <topic>        — Write-focused: walkthrough → wiki page (always writes)
/study-walkthrough -c work|personal       — Preselect category for a new wiki page (inherits when extending)
/study-walkthrough --from <url>           — Walkthrough from URL content
/study-walkthrough <pasted text>          — Walkthrough from provided text
```

## Category

Every wiki page written or extended by this skill carries a `category`. Follow `references/category-policy.md` to resolve it — extending inherits from the existing page (never overwrite); creating prompts in Phase 1 Step 4 (write-focused) or before the first write (deepen-focused) unless `-c` was passed. Propagate the resolved value to any chained `/study-flashcard` session.

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

**Step 1 -- Find what exists:**

1. Read `wiki/.wiki-index.json` for the topic
2. Run `treesearch search --query "<topic>" --index_dir wiki/indexes` for keyword matches
3. Run `scripts/wiki-search "<topic>"` for semantic matches (if Ollama running)
4. Call `find_similar_cards` from MCP to find related flashcards

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

- **Category** (closed set): `work` or `personal`. If extending an existing page, inherit from that page. If `-c` was passed, use it. Otherwise ask once. This value goes into the new page's `category` frontmatter and flows to any chained flashcard creation.

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
- Show concrete codebase code, never abstract examples
- Ask predictions before revealing answers
- **Probe when possible.** For code-shaped concepts (git, Python, shell, SQL, API behavior, algorithms), ask the developer to actually run a minimal snippet and paste the output — `uv run python -c`, a repl one-liner, a `git` command, `curl | jq`, a unit test. Compare the output against the prediction they made in the concrete challenge step. Probes turn Assumed understanding into Known and catch the "I thought I knew this" failure mode that pure discussion misses. Skip probes for theory-only concepts where no small snippet would demonstrate the point.
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

**Write-focused mode** -- proceed directly to wiki write:

1. Present the full draft wiki page with frontmatter, wikilinks, and all sections
2. For each section: ask the developer to explain it in their own words. If they cannot, discuss until they can.
3. Adjust the page based on gaps surfaced during review
4. **Probe sections:** Default `probe_sections` to all H2 headings except `Related Concepts`, `References`, `See also`, and `TL;DR`. Offer the developer a chance to mark any remaining sections as reference-only — but default-all is usually correct. Write `probe_sections` in frontmatter and seed `last_probed` with the same list (keeps the queue invariant `set(last_probed) == set(probe_sections)` true from day one; first review rotates as if fresh).
5. Follow `references/wiki-write-protocol.md` for the full write flow
6. Log the session

**Deepen-focused mode** -- offer choices:

1. **"write wiki"** -- Follow `references/wiki-write-protocol.md`. (Preflight was already run up front — no re-run needed.)
   - If extending an existing page: add new sections for the deeper material, increment `depth` frontmatter (e.g., depth 1 -> 2), set `last_deepened` to today. If any new H2 sections were added, extend `probe_sections` to include them (excluding `Related Concepts`, `References`, `See also`, `TL;DR`) **and reset `last_probed` to match the new `probe_sections`** so the queue invariant holds (avoids a persistent `probe-rotation-drift` lint error between now and the next review).
   - If creating new: draft a full page with `depth: 1` and everything covered. Set `probe_sections` to all H2s except the reference-only set; seed `last_probed` with the same list.
   - Include `flashcard_ids` for any related cards
   - Run `scripts/wiki-write`, append session log

2. **"add flashcard"** -- Chain to `/study-flashcard` for concepts that need SRS reinforcement, especially the ones that were initially failed during calibration

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

**Session log** -- always append to `logs/YYYY-MM-DD.md`:

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

### 6. Warnings/Notes
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
- Calibrate before teaching -- never assume the developer's level
- Loop on failed recall -- never skip past a gap
- Use concrete codebase code, not abstract examples
- Log every session, even if no wiki write happens
- Track which concepts are new vs. reinforced for accurate logging

**Never:**
- Skip calibration when existing material exists
- Move past a concept the developer can't explain back
- Dump information without checking understanding
- Auto-write to wiki without developer requesting it (deepen-focused mode)
- Create flashcards automatically -- always offer, never force

## Developer Preference — Intuition First, Syntax as Reference

The developer wants walkthroughs and wiki pages centered on **high-level intuition and evaluation capacity** — tradeoffs, design principles, mental models, "when/why X over Y," threat models, failure modes, and concepts portable across languages/frameworks.

Syntax details (exact API signatures, flag defaults, enum values) **are welcome in walkthroughs and wiki pages** — they make the reference material useful. Lead with the intuition, include the syntax as supporting reference.

**Hard rule for the flashcard handoff:** if this session chains into `/study-flashcard`, do NOT propose syntax-recall cards. Only concept/tradeoff/intuition cards make it into the SRS. Syntax stays on the wiki page as a lookup.
