---
name: study-walkthrough
description: "Explore a topic hands-on: builds an interactive explorable page (animated step-throughs, lever sandboxes, break-it scenes, predictions) scene by scene, then discusses the developer's questions, optionally challenges them Socratically, and writes the wiki page. Trigger keywords: deepen, walkthrough, explore, explorable, study deeper, revisit, create reference, document this pattern."
user_invocable: true
---

# /study-walkthrough: Explore, Discuss, Challenge, Write

The developer explores a topic first, in an **explorable**: a small interactive page built scene by scene, published as a private claude.ai Artifact. Then they bring their questions to Claude, optionally get challenged further, and the session ends with a wiki page that links the explorable.

**Core guarantee:** the developer finishes understanding the mechanism, not having read about it. Every scene made them predict before it revealed, every miss is recorded, and the misses drive the discussion, the challenge and the flashcards.

**Read `references/explorable-design.md` before storyboarding.** It holds the research behind the format, the scene catalogue, the motion rules, the technical contract and the `db` schema. This file is the session flow.

## Wiki Integration

This skill reads from and writes to the developer wiki at `wiki/`. See `references/wiki-write-protocol.md` for the full "write wiki" flow, linking rules, and frontmatter spec. "Show in Omvida" works at any point (the protocol's flow).

## Session Rules

For additional shared interactive principles (scope, handling disagreement, non-interactive mode), see `~/.claude/skills/references/interactive-principles.md`.

- **One scene per turn.** Build it, smoke-test it, publish it, end the turn with one line on what to try. Never build the whole page in one go: one scene is under a minute of waiting, a whole page is a slot machine (AGENTS.md, anti-slot-machine).
- Start each phase with `Phase X/5: <title>`. Pause after each phase; never auto-advance.
- If the developer says "skip" or "I know this", fast-forward immediately.
- **Read silently, never cat.** `mcp__qmd__query`, `Read` of wiki/index/log files, `mcp__flashcard-mcp__*`, `ArtifactData` reads and `scripts/explore-check` run without narration and without echoing output. The chat shows only synthesized output: the storyboard, the scene link, the misses, the next question.

## Answering vs. Socratic: by phase

The explorable reveals by design: the developer predicts, then sees. What Claude says in chat depends on the phase:

- **Discuss (Phase 3): answer directly.** The developer explored first and now asks. Answer concisely, grounded in the research facts, and cite a source URL when a claim is version-specific or non-obvious. Then check the answer landed with one small follow-up question, not a quiz.
- **Challenge (Phase 4): Socratic never-reveal.** The developer produces every answer. One small question at a time. On a wrong or blank answer, decompose into a smaller, more concrete question (a specific value, a one-line snippet, a named scenario); never state the answer to fill the gap. "Make it concrete" or "I don't understand" is a request for a smaller *question*, not for the answer. Confirming a correct answer is fine; saying it first is not. An explicit "just tell me" is honored, then re-probed.
- **The explorable and the wiki page are reference material** and state the facts. The prediction gate is what keeps the page from handing them over unearned.

## Running Ledger

For sessions longer than ~3 phase messages, keep a tiny ledger at the top of each phase message (one line per field, skip empty fields):

- **Explorable:** the artifact URL, `scene k/n published`
- **Missed:** predictions or challenges the developer got wrong (scene id + one phrase)
- **Open questions:** from the page's Ask box or the chat, not yet resolved
- **Queued:** flashcard / wiki deltas to propose at Phase 5

Chat-only; never written into the wiki page.

## Output Contract: Progress Footer

While the flow is active, end every assistant message with a progress footer as its last line, including clarifying questions and short acknowledgements:

- With steps: `Scene 2/5 · Phase 2/5 — Explore`
- Without steps: `Phase 3/5 — Discuss`

Omit it only when the developer opted out of the interactive flow (non-interactive subagent mode, an explicit one-shot request).

## MCP and Tool Dependencies

- `flashcard-mcp`: `check_pressure`, `find_similar_cards`, `search_cards`, `get_card`.
- **Artifact** tool: publish the explorable (load the `artifact-design` and `artifact-capabilities` skills first, as that tool requires); **ArtifactData** (deferred; load via ToolSearch) to read the page's `attempts` and `questions`.
- `scripts/explore-check`: headless smoke test before each publish.

## Research Grounding

Scenes state facts, and the in-page Ask answers from a fact sheet, so both must come from sources, not model memory. At Phase 1 Step 1, run the **`research-grounding` workflow** (`.claude/workflows/research-grounding.js`) in the background, in parallel with the wiki lookups.

**Two lanes, not equal:**

- **Authoritative lane (ground truth):** official docs, specs, RFCs, source code. Decides what is *factually true*.
- **Practitioner lane (opinion):** blog posts, talks, forum threads. Adds tradeoffs, lived experience, gotchas. Always labelled opinion, attributed, and marked `consensus` / `contested` / `single-voice`.

**The hard rule: authoritative wins for facts.** A practitioner claim flagged `contradictsGroundTruth` is dropped; an opinion is never promoted to a fact.

**Invoking the workflow.** Call the `Workflow` tool with `name: "research-grounding"` and `args` as a **real JSON object, never a JSON-encoded string**: `args: { "topic": "<the developer's full topic, verbatim>", "cadence": "learning" }`. This skill instructing you to call it IS the opt-in. It runs in the background and notifies on completion.

| arg | value |
| --- | --- |
| `topic` | the walkthrough topic |
| `cadence` | `learning` \| `refresh` \| `concise` (`concise`/`refresh` → 1+1 agents, `learning` → 2+2) |
| `thoroughness` | optional `lite` \| `normal` \| `deep` (`deep` = 3+3, for architecture/pattern topics) |
| `fromUrl` | the URL (or a note that text was pasted) for `--from` / pasted-text invocations |

It returns `{ confidence, authoritativeSources[], practitionerSources[], facts[], loadBearing[], misconceptions[], opinions[], divergence[] }`.

**Using the findings:**

- **Scenes:** `loadBearing` facts decide what the scenes show; `misconceptions` are the best prediction options (the wrong answer people actually hold). A scene built before the research returned is checked against it when it lands: a contradicted point is corrected in place and the scene republished, with one line in chat.
- **Fact sheet:** the page's in-page Ask is grounded in a constant listing the relevant `facts` with source URLs (`explorable-design.md`, "In-page Ask").
- **Discuss:** facts ground the direct answers; `opinions` and `divergence` become tradeoff answers presented as opinion ("practitioners disagree: ...").
- **Challenge:** `opinions` unlock judgement questions ("here's a gotcha someone hit in production: why might that happen?"). Never pose a `contradictsGroundTruth` opinion.
- **Wiki write:** facts go to `## References` (inline-link version-specific claims); load-bearing opinions to `## Tradeoffs & Gotchas` or inline `> [Note]` callouts, attributed.
- **`confidence: low`:** fewer facts in scenes, more probes, and a `> [Note] Sources sparse. Verify before relying on this page.` callout on the wiki page.

**Silent execution.** Don't narrate the workflow or paste its output. If it fails, fall back to one background research subagent with the prompt below; if that fails too, say one line ("research unavailable, proceeding from model knowledge, flagged on the page") and continue.

**Single-agent fallback prompt:**

> Research `<topic>` for a developer walkthrough across two lanes, kept separate. **Authoritative (ground truth):** find 2-3 official docs / RFCs / source / canonical refs (`WebSearch` then `WebFetch`); return load-bearing facts, each tagged with its source and confidence. **Practitioner (opinion):** find 1-2 credible blog posts / talks / forum threads; return tradeoffs, experiences, architectural nuances, and gotchas, each tagged with its source and stance (consensus | contested | single-voice). Then reconcile: authoritative wins for any factual conflict; flag practitioner claims that contradict a fact as likely stale/wrong, never promote an opinion to a fact. Return `confidence` (high|medium|low), the authoritative facts, the labelled opinions, misconceptions/version gotchas, and any practitioner divergence, as terse structured findings with no preamble.

**Skip research only** for repository-internal topics (a codebase pattern, an internal script); note it in the session log's `Research:` field.

**Probes are exempt.** When the developer runs a snippet and pastes the output, that output is the ground truth for what it demonstrates. If it contradicts the research, surface it ("the docs say X but your run shows Y, let's dig into why").

## Invocation

```
/study-walkthrough                        start (asks for the topic)
/study-walkthrough <topic>                explore a topic
/study-walkthrough --write <topic>        explore, then always write the wiki page
/study-walkthrough --from <url>           explore what a URL teaches
/study-walkthrough <pasted text>          explore the text's key ideas
/study-walkthrough --no-explore <topic>   no page: straight to Discuss and Challenge in chat
```

Omvida's "Go deeper" and Add → Wiki entry open this skill with a `Context: wiki page [[folder/slug]]` line. Read that page silently. If it already has `explorables`, **extend that explorable** with scenes for the new depth (same source file, published to its existing URL, see Phase 2) instead of starting a new one.

## Mode and Cadence

**Mode** sets the output:

- **Write-focused:** `--write`, `--from`, pasted text, or no existing page and the intent is clearly "document this". Phase 5 writes the wiki page by default.
- **Deepen-focused** (default): Phase 5 offers the wiki write, flashcards, or done.

**Cadence** sets the depth. Default **Learning**:

| Cadence | Explore | Discuss | Challenge |
| --- | --- | --- | --- |
| **Learning** | 4-6 scenes | full | offered, recommended |
| **Refresh** (existing page, or "just refresh") | reuse the page's explorable; 1-2 new scenes only for gaps calibration found | on the gaps | on the gaps |
| **Concise** | 1-3 scenes, or none | short | one question, no looping |

Announce the cadence with the storyboard. If the developer keeps saying "I know this" (→ Refresh) or "wait, show me that again" (→ Learning), suggest a switch once; never switch silently.

## Correction Primitive

When the developer corrects something (a scene's behaviour, a fact, an earlier answer):

- **Edit it in place**: the scene in the source file (then republish), the chat statement, the wiki draft. Never append "actually, X".
- A correction that invalidates a drafted card or wiki section marks it `[STALE — redraw]`; redo it before advancing.
- One line in chat: "Updated scene 2: the cookie is now omitted on cross-site POSTs."

## Preflight: SRS Pressure Check

Run it before Phase 1 and before any other tool call. The first assistant message of this skill is the pressure-check output and nothing else, regardless of mode or flags. Follow `references/srs-pressure-check.md` exactly:

1. Call `mcp__flashcard-mcp__check_pressure` (not `get_due_cards` or `list_decks`).
2. `ok` → one line: `SRS pressure: ok — proceeding.` `warn` / `pause` → counts, reasons and clearance numbers, then the gate question; wait for an explicit answer.
3. Footer: `Preflight — SRS Pressure Check`.

## Phase Flow

### Phase 1/5: Scope & Storyboard

**Step 1: find what exists, start research (parallel, silent).**

1. Read `wiki/.wiki-index.json` for the topic.
2. `mcp__qmd__query` (hybrid, `rerank: false`) on `<topic>`.
3. `find_similar_cards` on the topic.
4. Start the `research-grounding` workflow in the background (see Research Grounding).

**Step 2: present what exists and calibrate, in one message.** Name existing pages with their `updated` date, their explorable if they have one, and the card count. Then **one** calibration question:

- Existing material: one targeted recall question from the page or the hardest card back.
- None: "What do you already know about <topic>, and what do you want to be able to do after this?"

**Step 3: storyboard.** From the calibration answer, propose 3-6 scenes (per cadence), one line each: the scene's question, its type from the catalogue, and the prediction it asks. Lead with the hook scene (the most surprising behaviour). For write-focused mode, add the page type (Tutorial/Concept, Problem-Solution, Pattern/Technique, Feature/Tool Overview) and scope: a topic with >5 sub-concepts → suggest splitting; a single fact → suggest adding it to an existing page.

> 1. **Why does bank.com get the cookie?** Step-through: a forged form submit. *Predict: does the browser attach bank.com's cookie to a POST from evil.com?*
> 2. **What does SameSite change?** Lever sandbox: Strict / Lax / None × GET link / POST form / fetch. *Predict: which cells carry the cookie under Lax?*
> 3. ...
>
> Edit, reorder, drop, or `go`.

Wait for the developer's go. The storyboard is the contract for Phase 2.

### Phase 2/5: Explore (scene by scene)

**Per scene:**

1. **Build** the scene into `explore/<folder>/<slug>.html` per `references/explorable-design.md`. Scene 1 also creates the page shell (header, stepper, fact sheet, recording, Ask box). The key `<folder>/<slug>` is the wiki page it belongs to; for a new topic, pick the key the page will get now.
2. **Smoke-test:** `scripts/explore-check <file> --out <scratchpad>/explore-shots` loads the page from disk (so without capabilities) in headless Chromium at desktop and phone width, and exits 1 on an uncaught error. Read both screenshots silently and fix what's off before publishing: errors, overflow, overlapping labels, an empty diagram.
3. **Publish** with the Artifact tool from the same file path every time (same URL). First publish: `capabilities: {db: {}, sample: {}}`, a two-to-four-word title, `icon` (e.g. `lightbulb`); then one functional pass, an `ArtifactData` `list` of `attempts` and `questions` (both may be empty), and one line saying what was checked. Later publishes: omit `capabilities` and `icon`. **Extending an explorable from an earlier conversation:** `Artifact` `read` its URL (from the page's `explorables`) first, then publish with `url` set to it; without `url` the publish creates a second artifact.
4. **End the turn** with one line: the link (first scene) or "scene k is live", plus what to try. "Scene 1 is live: predict before you step. Say `next` when done, or ask in the page."

**When the developer comes back** ("next", a reaction, a question):

- Read the page's `attempts` (and `questions`) with `ArtifactData` `list`, silently. Misses are as `explorable-design.md` (Recording) defines them, this session's only. A missed prediction goes into the ledger's **Missed** with one line in chat: "You expected the cookie to be blocked on the POST; that one's queued for Discuss."
- A request to change the scene ("slower", "add a step", "this label is confusing") → change it in place and republish before moving on.
- A question typed in chat → answer it directly if it is short (Discuss rules); a big one goes to Open questions for Phase 3.
- Then build the next scene.

After the last scene: "That's the whole page. Want to discuss what came up, or go straight to a challenge / the write?"

### Phase 3/5: Discuss

1. Read `attempts` and `questions` once more. Open with what the page recorded, then hand over:
   > You missed 2 of 5 predictions (scenes 2 and 4) and asked one question in the page (about Lax and top-level navigations). Where do you want to start?
2. The developer drives. Answer directly, grounded in the facts (see "Answering vs. Socratic"). One concept per message.
3. When a question is best answered visually, **offer** a clarifying scene ("I can add a scene that steps through exactly that, want it?"). Build it only on yes, per the Phase 2 loop.
4. Before leaving the phase, walk each **Missed** item once: ask the developer how they'd now predict it. A still-wrong answer stays in Missed for the challenge and the flashcards.
5. Close: "Anything still fuzzy? Otherwise: a challenge, write the page, or done."

### Phase 4/5: Challenge (optional)

Offered, never forced. Recommended in Learning cadence and whenever Missed is non-empty. **Socratic never-reveal applies here.**

- 2-4 challenges, each a single question that makes the developer **produce** something: transfer the mechanism to a new setting, predict a variant the page didn't show, find what breaks if a step is skipped, design the attack or the fix. Target the Missed items and the scenes' combined levers first.
- **Probe when possible:** for code-shaped concepts, ask the developer to run a minimal snippet (`curl`, a repl one-liner, a test) and paste the output; compare with their prediction. Capture a load-bearing probe takeaway (Prediction / Command / Output / Takeaway) in the session log.
- A challenge that is better interactive (a broken config to fix, a sort with a twist) can be an extra **challenge scene** in the page; its answers land in `attempts` with `kind: "challenge"`. Offer it; build on yes.
- On a miss: decompose into a smaller question until the developer gets there (Learning, Refresh), or note it and move on (Concise). Never reveal.

### Phase 5/5: Write & Chain

**Before drafting**, internalize the "Writing Style" section of `references/wiki-write-protocol.md`: **no em dashes anywhere**, **no prose-colons as clause connectors**. Filename = slugified title (lint error otherwise); pick the filename first.

**Write-focused mode:** proceed to the wiki write. **Deepen-focused:** offer:

1. **"add flashcard":** chain to `/study-flashcard <topic>` with `Context: explorable <url>`. It seeds its suggestions from the page's misses (concept/intuition cards only, see Developer Preference).
2. **"write wiki":** the write below.
3. **"done":** log the session, no writes.

**The wiki write** (follow `references/wiki-write-protocol.md`):

1. Present an outline first: title and H2 sections, one line each. Wait for confirmation.
2. Draft the page. It is the reference artifact: it states the facts, compactly, and does not repeat the scenes' prose. A page extending an existing one adds H2 sections, keeps existing links and sets `updated` to today.
3. **Frontmatter `explorables: [<artifact url>]`** (append to an existing list when this was a new explorable; unchanged when one was extended).
4. Include `flashcard_ids` for related cards, `## Related Concepts`, `## References`, and `## Tradeoffs & Gotchas` when practitioner opinion is load-bearing (see Wiki Page Structure).
5. Run `scripts/wiki-write <page>`, then offer "show in Omvida": the page now has an Explore button.

**Session log:** append to `logs/<MM>/<YYYY-MM-DD>.md`:

```markdown
## Session N — Walkthrough (HH:MM)
- **Topic:** CSRF and SameSite cookies
- **Mode:** deepen-focused
- **Cadence:** learning
- **Starting level:** knew the attack shape, not why SameSite=Lax still allows top-level GETs
- **Explorable:** https://claude.ai/artifact/... (`explore/security/csrf.html`, 5 scenes)
- **Predictions:** 3/5 right; missed scene 2 (Lax on POST), scene 4 (token in cookie vs. form)
- **Questions:** 2 in the page, 1 in chat (Lax+POST two-minute window)
- **Challenge:** 3 asked, 2 right first try, 1 after decomposing
- **Wiki updates:** [[security/csrf]] extended with 2 sections, `explorables` added
- **Flashcards:** 2 created from misses
- **Research:** research-grounding — 2 authoritative (RFC 6265bis, MDN) + 2 practitioner; confidence: high
- **Surprising:** expected Lax to block every cross-site POST; the misses say the token-vs-cookie distinction was the real gap
- **Heuristic:** SameSite is a default-deny for subresources, not a CSRF defence on its own
- **Next-time unblocker:** a scene that replays the same attack under each SameSite value side by side
```

Look-back fields are mandatory in Learning, recommended in Refresh, and collapse to one **Takeaway:** line in Concise. If nothing surprised, write `Surprising: none — cadence may have been too shallow`.

## Wiki Page Structure (for new pages)

1. **Frontmatter:** required `title`, `aliases`, `tags`, `created`, `updated`, `source_skill`, `flashcard_ids`; optional `explorables`.
2. **Title (H1):** descriptive for concepts, imperative for how-tos, "Careful:" / "Warning:" prefix for gotchas.
3. **Opening context** by page type: Tutorial/Concept → `## TL;DR`; Problem-Solution → context, `## The problem`, `## How to fix it`; Pattern/Technique → straight into the pattern; Feature/Tool Overview → what is possible, then a section per feature.
4. **Code examples:** minimal but working; `# bad` / `# good` comments; codebase code when possible.
5. **`## Related Concepts`:** `[[absolute/path]]` wikilinks with a one-line relationship each.
6. **`## Tradeoffs & Gotchas`** (when practitioner opinion is load-bearing): attributed, marked consensus/contested, never ground truth; drop `contradictsGroundTruth` opinions. One-offs go inline as `> [Note]`.
7. **`## References`:** up to 4 authoritative URLs with a one-line "what this is"; practitioner sources under a `**Practitioner / opinion:**` sub-label. A factual body claim is never cited only to a practitioner source. Research skipped or unavailable → `_None — repo-internal topic._` or `_Research unavailable at write time; verify before relying on this page._`
8. **Warnings/notes:** short ones bold inline; standalone `> [Warning]` / `> [Note]`.

Writing style: concise, technically precise, practical, insightful, no emojis.

## Chaining

**Into /study-walkthrough:** `/study` lapses on a topic ("2 lapses on CSRF, explore it?"); Omvida's Go deeper and Add → Wiki entry; `/study-flashcard` when a topic is new to the developer.

**Out of /study-walkthrough:** `/study-flashcard` with the explorable as context (cards from misses); `/study` to review related cards right away. Offer one at a time.

## Guardrails

**Always:**
- Preflight first; storyboard approved before the first scene.
- One scene per turn, smoke-tested before every publish, always published from the same source path.
- Every scene asks one question and gates its reveal behind a prediction.
- Read the page's `attempts` and `questions` when the developer comes back, and let the misses drive Discuss, Challenge and the flashcards.
- Ground scenes and the fact sheet in the authoritative research; opinions stay labelled.
- Log every session, even with no wiki write.

**Never:**
- Put a wall of text, autoplay motion or decoration in a scene (`explorable-design.md`, Anti-patterns).
- Reveal answers in the Challenge phase (explicit request excepted).
- Present a practitioner opinion as fact, or cite a factual claim only to a blog.
- Auto-write the wiki page in deepen-focused mode, or create flashcards without the developer picking them.

## Developer Preference: Intuition First, Syntax as Reference

The developer wants **high-level intuition and evaluation capacity**: tradeoffs, design principles, mental models, "when/why X over Y", threat models, failure modes, concepts portable across languages. Scenes should make *mechanisms* visible, not quiz syntax. Syntax details (API signatures, flag defaults) are welcome on the wiki page as lookup material.

**Hard rule for the flashcard handoff:** no syntax-recall cards. Only concept, tradeoff and intuition cards enter the SRS.
