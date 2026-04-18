# Study Workspace

Personal development workspace combining daily rituals, spaced repetition flashcard review, and a developer wiki. Uses the [flashcard-mcp](../flashcard-mcp) SRS system via MCP. Inspired by the [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern — but content only enters through interactive skills, never raw ingestion.

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

`todo.md` at project root is a single ordered list of todos — top = highest priority, bubbles up during `/kickoff`. Simple markdown checkboxes. Read and updated by `/kickoff` and `/end` — not a project management tool, but a thinking artifact for setting focus, boundaries, and intentions.

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

## Session Logs

Daily append-only logs in `logs/YYYY-MM-DD.md`. Each session records: skill used, topic, cards reviewed/created, accuracy, lapses, wiki updates, duration.

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

Python modules live in `scripts/wiki/`. The top-level scripts are thin entry points.

## Dependencies

- **TreeSearch**: `uv tool install pytreesearch` — FTS5 search for wiki
- **Ollama**: Local LLM runtime with `nomic-embed-text` model — semantic embeddings
- **Obsidian**: Optional, for graph visualization and enhanced health checks. Launch with `snap run obsidian`.
