# Study Workspace

Personal development workspace combining daily rituals, spaced repetition flashcard review, and a developer wiki. Uses the [flashcard-mcp](../flashcard-mcp) SRS system via MCP. Inspired by the [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern — but content only enters through interactive skills, never raw ingestion.

## Skill Design Principles

Applies to every skill in this repo.

- **Anti-slot-machine.** No skill step may end in "go do extensive work — come back later for the result." If a step would require more than ~30s of hands-off waiting before the developer's next decision point, split it smaller or surface progress. The mandatory SRS pressure preflight is the canonical example of this rule: it refuses to start a session when the deck is overloaded, rather than inviting the developer into a fire-and-forget loop. Skills should similarly favor tight feedback over variable-reward batching.
- **Human is the agent.** The developer drives. Skills ask before deciding on ambiguity and never silently auto-advance past an unresolved quality issue, gap, or correction.
- **Small, verifiable steps.** One concept per message. Predict before revealing. Probe when possible. Loop on failure rather than moving on.
- **Look back.** Every substantive skill session captures what was surprising and what heuristic generalizes — see the session log templates in each skill.
- **Correct in place.** When the developer corrects something, edit the prior statement rather than appending a contradiction.

## Available Skills

### Daily Rituals

- `/kickoff` — Start or refocus a session. Fixed check-in questions, todo reorder around stated focus, motivational interview (opens with time-framing, continues into coaching). Can run multiple times per day; delta cadence for refocus runs. Logs session.
- `/end` — End-of-day ritual. Reviews git activity and session logs, reflection interview, todo update. Logs session.
- `/progress` — Cross-day/week progression check. Reads recent commits + session logs (window = since last `/progress`, 14-day fallback, or `7d`/`30d` override), asks calibrating questions, states a falsifiable Growth/Drift/Tension hypothesis, gives one piece of feedback, auto-offers `/reflect`. Logs session.
- `/reflect` — Deeper motivational interview on general development trajectory (multi-day/week), not tied to a block or today. Opens with three fixed anchors (growing-into / pattern / better version), then free MI. Logs session.

### Study & Knowledge

- `/study` — Interactive study session. Claude evaluates answers and rates them. Logs sessions.
- `/study-flashcard` — Create new flashcards through a guided walkthrough with duplicate detection. Optionally writes companion wiki pages.
- `/study-walkthrough` — Interactive walkthrough that calibrates to current understanding, fills gaps, pushes deeper. Optionally writes wiki pages. Use `--write` to default to producing a wiki page.
- `/obsidian-check` — Launch Obsidian, run wiki health checks, open pages in GUI.

## Todo

`todo.md` at project root has two headings: `## Today` and `## Backlog`. `## Today` is the short list the developer commits to for the current day (set at the first `/kickoff` of the day); it is auto-cleared at the next day's first kickoff — unchecked items roll back to `## Backlog`, checked items are dropped. `## Backlog` is the ongoing ordered list — top = highest priority. Read and updated by `/kickoff` and `/end` — not a project management tool, but a thinking artifact for setting focus, boundaries, and intentions.

## Wiki

The wiki lives in `wiki/` (Obsidian vault). Pages are organized by topic folders (e.g., `wiki/javascript/react/`, `wiki/security/`).

### Page Format

Every wiki page has YAML frontmatter with required fields: `title`, `aliases`, `tags`, `created`, `updated`, `source_skill`, `probe_sections` (non-empty list of H2 headings the page will be probed against at review time), `last_probed` (queue that rotates during review — seed with `probe_sections` on a new page). Optional: `flashcard_ids`, `depth`, `last_deepened`, `next_review`, `review_interval`, `allow_orphan` (set to `true` to suppress the orphan warning for pages that are intentionally standalone).

### Linking Rules

- All wikilinks use **absolute paths** from wiki root: `[[architecture/cqrs]]` not `[[cqrs]]`
- Page filename = slugified title (lowercase, hyphens, no special chars)
- Aliases declared in frontmatter, checked against index for uniqueness
- Obsidian is configured with `newLinkFormat: absolute` in `wiki/.obsidian/app.json`

### Index

`wiki/.wiki-index.json` tracks all pages with their titles, aliases, sections (H2 headings), tags, and flashcard IDs. Updated automatically by `scripts/wiki-write`.

### Search

- **TreeSearch** (pytreesearch): FTS5 keyword search, <100ms, section-aware results. Index at `wiki/indexes/`.
- **Ollama** (nomic-embed-text): Semantic embeddings pre-computed at write time, stored in `wiki/.embeddings.json`. Query via `scripts/wiki-search`.

### Writing to Wiki

All skills follow the shared protocol in `.claude/skills/references/wiki-write-protocol.md`. The flow: read index → extend/split check → draft → link resolution → write file → `scripts/wiki-write` (updates index, reindexes TreeSearch, embeds via Ollama, runs lint) → session log.

### Linting

`scripts/lint` checks: broken wikilinks, absolute path enforcement, frontmatter completeness, orphan pages, alias collisions, slug/filename consistency, flashcard ID drift between frontmatter and index. Runs automatically after every wiki write.

Results are split into **errors** (block clean status, exit 1) and **warnings** (informational, exit 0). Orphan pages are warnings — suppress per-page with `allow_orphan: true` in frontmatter. Wikilink parsing ignores fenced code blocks, inline code, and image embeds (`![[...]]`), and strips `#heading` anchors and `|display` pipes before resolving targets. Self-links do not count as inbound.

Python code is linted with ruff: `uv run ruff check scripts/ tests/`. Config lives in `pyproject.toml`.

### Show in Obsidian

At any point during any skill, the developer can say "show in Obsidian" to launch the app and open the relevant page. Check if Obsidian is already running before launching — only start it if not:

```bash
pgrep -f "obsidian" >/dev/null 2>&1 || (snap run obsidian &>/dev/null & disown && sleep 3)
```

Then open pages with `obsidian open vault="study" file="<slug>"` (use bare slug, not path — `path=` does not work). Never run `snap run obsidian` unconditionally — it breaks when Obsidian is already open.

## Probes

`probes/` is where `/study-walkthrough` Probe mode saves load-bearing runtime checks — the portable analog of Solveit's live kernel. One markdown file per probe, four sections (Prediction / Command / Output / Takeaway), committed. See `probes/README.md` for the full format spec and the three-tier dependency model (inline → topic env → scratch project). Only persist probes that changed the developer's understanding; skip the ones that merely confirmed what was already known.

## Query Protocol

When the developer asks a substantive knowledge question — any "what is X / how does X work / why does X" or equivalent — handle it through this flow. The guiding principle: **never block the first answer on lookups**. Answer from memory immediately; run saved-knowledge lookups in the background and reconcile afterward.

1. **Answer first, from memory.** Give the developer your best answer right away based on your own knowledge. Do not run `scripts/wiki-search`, `mcp__flashcard-mcp__search_cards`, or any other lookup before this first response — those are slow (Ollama embedding round-trip) and would block the reply.

2. **Spawn one background subagent to do all lookup + verification + logging in parallel.** Immediately after (or alongside) the first answer, launch a single background agent (`run_in_background: true`) with a prompt that instructs it to:
   - Run `scripts/wiki-search "<query>"` and collect top hits.
   - Call `mcp__flashcard-mcp__search_cards` with the same query.
   - Optionally glance at `wiki/.wiki-index.json` sections/aliases if phrasing is unlikely to embed well.
   - **Always verify the memory answer against the web** via `WebSearch` (and `WebFetch` on the most authoritative result — official docs, source code, RFC, upstream repo — when the question has a specific factual claim to check). This runs regardless of whether wiki/cards hit, so memory answers are never trusted on their own.
   - Append a `## Query N (HH:MM)` entry to today's `logs/YYYY-MM-DD.md` (creating the file if missing) with: **Question**, **Wiki hits** (wikilinks or `none`), **Card hits** (ids + one-line fronts or `none`), **Web check** (one-line verdict: `confirms` | `contradicts: <what>` | `refines: <what>` | `inconclusive`, plus the authoritative URL used), **Source** (`wiki` | `cards` | `research` | `mixed` | `memory`), **Answer** (one-line summary of what you told the developer).
   - Report back the wiki/card hits **and the web-check verdict** so the main thread can reconcile.

   The main thread must not `Read` or `Write` the log file itself, and must not run wiki-search / card-search directly. Same rule for the wiki-write follow-up when the developer accepts a `/study-walkthrough --write` offer: spawn it in the background.

3. **Reconcile when the subagent returns.** Once the background agent reports hits + web verdict:
   - If the wiki/cards **confirm** your answer, add a brief follow-up citing the page(s) with `[[folder/slug]]` wikilinks or flashcard ids. Keep it short — the developer already has the answer.
   - If the wiki/cards **contradict or correct** your answer, post a correction immediately, citing the saved knowledge. Do not let a wrong memory-answer stand.
   - If the **web check contradicts** the memory answer (even when wiki/cards are silent or agreed with memory), post a correction citing the authoritative URL. Web truth wins over stale memory and stale wiki both.
   - If the **web check refines** the answer (adds a caveat, version note, edge case), extend the original answer with the new detail and cite the URL.
   - If **only flashcards** cover it, cite the ids and note the wiki gap — offer `/study-walkthrough --write` to promote the concept into a proper page.
   - If **no coverage** in wiki or cards, offer `/study-walkthrough` (append `--write`) to capture the topic. Do not silently auto-write.

4. **Never skip the log, even when answering from memory is tempting.** The log is how we see which topics recur and which warrant a wiki page. A one-liner is fine; this is a thinking artifact, not a report. The background agent owns this — the main thread only needs to spawn it.

Scope: this applies to knowledge/explanation questions. It does *not* apply to operational requests ("edit this file", "run the tests", "what did I just change") or to clarifying questions inside an active skill (`/study`, `/kickoff`, etc.) — those skills own their own flow.

## Session Logs

Daily append-only logs in `logs/YYYY-MM-DD.md`. Each session records: skill used, topic, cards reviewed/created, accuracy, lapses, wiki updates, duration.

**Always log repo changes.** Any change you make to this repo — skills, scripts, wiki, todo, config, AGENTS.md itself — must be recorded in today's `logs/YYYY-MM-DD.md` as a `## Session N — Change (HH:MM)` entry with **Files:**, **Change:**, and **Why:** fields. Do this even outside a kickoff/end ritual. If today's log doesn't exist yet, create it.

## MCP Server

The `flashcard-mcp` MCP server must be running. It starts automatically via `.mcp.json` (stdio transport pointing to `~/Code/Misc/flashcard-mcp/src/mcp/server.ts`).

If tools aren't available, check that `~/Code/Misc/flashcard-mcp` has dependencies installed (`npm install` in that directory).

## Development

Managed by **uv**. Run `uv sync` to install dependencies into `.venv/`.

```bash
uv run pytest           # run tests
uv run pytest tests/ -v # verbose
```

## Scripts

All scripts in `scripts/` are Python 3. They can be invoked either way:

```bash
scripts/wiki-write wiki/security/hsts.md   # direct (shebang)
python3 scripts/wiki-write wiki/security/hsts.md  # explicit
```

Available scripts:
- `scripts/wiki-write <page>` — Update index, reindex TreeSearch, embed via Ollama, run lint
- `scripts/lint` — Check broken wikilinks, frontmatter, orphans, alias collisions
- `scripts/wiki-search "<query>"` — Semantic search against wiki embeddings
- `scripts/wiki-due` — List wiki pages due for review
- `scripts/wiki-reschedule <page> <rating>` — Reschedule a wiki page after review (1-4), rewrites frontmatter and re-indexes
- `scripts/wiki-probes [<wiki-path>]` — List probes linked to a wiki page (derived from probe frontmatter). Omit argument to list all grouped by wiki page; `--topic <slug>` to match by topic folder instead; `--count` for count only

Python modules live in `scripts/wiki/`. The top-level scripts are thin entry points.

## Dependencies

- **TreeSearch**: `uv tool install pytreesearch` — FTS5 search for wiki
- **Ollama**: Local LLM runtime with `nomic-embed-text` model — semantic embeddings
- **Obsidian**: Optional, for graph visualization and enhanced health checks. Launch with `snap run obsidian`.
