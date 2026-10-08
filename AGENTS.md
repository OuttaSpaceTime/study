# Study Workspace

Personal development workspace combining daily rituals, spaced repetition flashcard review, and a developer wiki. Uses the [flashcard-mcp](../flashcard-mcp) SRS system via MCP. Inspired by the [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern — but content only enters through interactive skills, never raw ingestion.

## Skill Design Principles

Applies to every skill in this repo.

- **Anti-slot-machine.** No skill step may end in "go do extensive work — come back later for the result." If a step would require more than ~30s of hands-off waiting before the developer's next decision point, split it smaller or surface progress. The mandatory SRS pressure preflight is the canonical example of this rule: it refuses to start a session when the deck is overloaded, rather than inviting the developer into a fire-and-forget loop. Skills should similarly favor tight feedback over variable-reward batching.
- **Human is the agent.** The developer drives. Skills ask before deciding on ambiguity and never silently auto-advance past an unresolved quality issue, gap, or correction.
- **Small, verifiable steps.** One concept per message. Predict before revealing. Probe when possible. Loop on failure rather than moving on.
- **Look back.** Every substantive skill session captures what was surprising and what heuristic generalizes — see the session log templates in each skill.
- **Correct in place.** When the developer corrects something, edit the prior statement rather than appending a contradiction.
- **Read silently, never cat.** Skills run `Read`, `Bash`, MCP calls, and `scripts/*` lookups *silently*. The chat shows only synthesized output — questions, verdicts, ratings, the next prompt — never raw file contents, command stdout, JSON dumps, or tool-result expanders. If a tool errors, surface a one-line summary, not the stderr blob. State intent in one short sentence per natural beat, not per call.

## Available Skills

### Daily Rituals

- `/kickoff` — Start or refocus a session. Fixed check-in questions, todo reorder around stated focus, motivational interview (opens with time-framing, continues into coaching). Can run multiple times per day; delta cadence for refocus runs. Logs session.
- `/end` — End-of-day ritual. Reviews git activity and session logs, reflection interview, todo update. Logs session.
- `/progress` — Cross-day/week progression check. Reads recent commits + session logs (window = since last `/progress`, 14-day fallback, or `7d`/`30d` override), asks calibrating questions, states a falsifiable Growth/Drift/Tension hypothesis, gives one piece of feedback, auto-offers `/reflect`. Logs session.
- `/reflect` — Deeper motivational interview on general development trajectory (multi-day/week), not tied to a block or today. Opens with three fixed anchors (growing-into / pattern / better version), then free MI. Logs session.

### Study & Knowledge

- `/study` — Interactive study session. Flashcards are the only thing reviewed: Claude evaluates answers and rates them. Closes by suggesting wiki pages related to the cards just studied (or the index view for free browsing). Logs sessions.
- `/study-flashcard` — Create new flashcards directly: suggests a few ready card fronts on a topic, the developer picks or edits them, they are created after the duplicate and quality checks. Not a walkthrough: for learning the topic, call `/study-walkthrough` or `/study`. Links new cards into an existing wiki page's `flashcard_ids`.
- `/study-walkthrough` — Interactive walkthrough that calibrates to current understanding, fills gaps, pushes deeper. Optionally writes wiki pages. Use `--write` to default to producing a wiki page.
- `/canvas` — Interactively edit an Obsidian `.canvas` in a tight edit→show→react loop. Two modes: **live** (`eval` against the running app, reads your GUI selection) and **file** (Read/Write the JSON on disk, git-trackable). Same JSON schema either way.

## Todo

`todo.md` at project root has two headings: `## Today` and `## Backlog`. `## Today` is the short list the developer commits to for the current day (set at the first `/kickoff` of the day); it is auto-cleared at the next day's first kickoff — unchecked items roll back to `## Backlog`, checked items are dropped. `## Backlog` is the ongoing ordered list — top = highest priority. Read and updated by `/kickoff` and `/end` — not a project management tool, but a thinking artifact for setting focus, boundaries, and intentions.

## Wiki

The wiki content lives in `wiki/`, organized by topic folders (e.g., `wiki/javascript/react/`, `wiki/security/`). The Obsidian vault is the **repo root** (name `study`); non-wiki content is hidden from it — see [Hiding non-wiki content](#hiding-non-wiki-content).

**Flashcards are the only thing studied; the wiki is for exploration.** Pages carry no review schedule and never become "due" — after the flashcard loop, `/study` Phase 4 offers pages connected to the cards actually studied (matched on `flashcard_ids`, falling back to tag overlap), or opens the index view to browse when nothing matches. The wiki-viewer surfaces the same link in reverse: each page has a flashcard modal, and `/flashcards` browses the whole deck.

### Page Format

Every wiki page has YAML frontmatter. Required on **all pages**: `title`, `aliases`, `tags`, `created`, `updated`, `source_skill`, `flashcard_ids` (list, empty `[]` is fine). `scripts/wiki-write` auto-fills `flashcard_ids` when missing; the rest must be set by the calling skill. Frontmatter is a **closed schema**: `scripts/lint` reports any key outside the required set plus `lint_ignore` as a `forbidden-field` error. That covers the retired scheduling fields (`next_review`, `review_interval`, `last_deepened`) and every earlier retirement (`depth`, `probe_sections`, `last_probed`, `allow_orphan`) without a list to maintain. Optional: `lint_ignore` (list of lint **warning** labels to suppress for this page — see [Suppressing warnings per page](#suppressing-warnings-per-page)).

### Linking Rules

- All wikilinks use **absolute paths** from wiki root: `[[architecture/cqrs]]` not `[[cqrs]]`
- Page filename = slugified title (lowercase, hyphens, no special chars)
- Aliases declared in frontmatter, checked against index for uniqueness
- Obsidian is configured with `newLinkFormat: absolute` in `wiki/.obsidian/app.json`

### Topics

A topic is a folder plus a tag; there are no index or map-of-content pages. Every page is tagged with its folder (and sub-folder) name, plus the subject tags it shares with pages elsewhere. The wiki-viewer and Omvida list a folder's pages from the tree, and Omvida's graph pulls pages that share a tag together, so a topic holds together without a hub page linking it. See the write protocol's "Topics" section.

### Index

`wiki/.wiki-index.json` tracks all pages with their titles, aliases, sections (H2 headings), tags, and flashcard IDs. Updated automatically by `scripts/wiki-write`.

### Search

- **qmd**: local hybrid search over `wiki/` — BM25 keyword + vector semantic search (RRF-fused), with optional LLM re-ranking, entirely on-device (no cloud calls). Query via the `mcp__qmd__query` MCP tool with `searches: [{type: "lex", ...}, {type: "vec", ...}]`. **Default `rerank: false`** for skill lookups (existence/relatedness checks) — warm latency is ~20-30ms. Pass `rerank: true` only when ordering quality matters more than speed — it costs ~8s per call every time (LLM cross-encoding is per-query compute, not a one-time load, so it never gets faster once warm). CLI equivalents: `qmd query "<text>" -c wiki` (hybrid+rerank), `qmd search "<text>" -c wiki` (BM25 only), `qmd vsearch "<text>" -c wiki` (vector only). Project config is `.qmd/index.yml` (tracked in git); the SQLite index at `.qmd/index.sqlite` is gitignored and rebuilt from wiki content. Embeddings refresh automatically as part of `scripts/wiki-write` (`qmd update` + `qmd embed`).

### Writing to Wiki

All skills follow the shared protocol in `.claude/skills/references/wiki-write-protocol.md`. The flow: read index → extend/split check → draft → link resolution → write file → `scripts/wiki-write` (updates index, refreshes the qmd search index, runs lint) → session log.

### Linting

`scripts/lint` checks: broken wikilinks, absolute path enforcement, frontmatter completeness, unknown/retired frontmatter fields, alias collisions, slug/filename consistency, and flashcard ID drift between frontmatter and index. Runs automatically after every wiki write.

Results are split into **errors** (block clean status, exit 1) and **warnings** (informational, exit 0). There is no orphan check: a page nothing links to is still reached through its folder and its tags. Wikilink parsing ignores fenced code blocks, inline code, and image embeds (`![[...]]`), and strips `#heading` anchors and `|display` pipes before resolving targets.

#### Suppressing warnings per page

Add a `lint_ignore` list to a page's frontmatter naming the warning labels to silence for that page (the label is the token before the first colon in the lint line, e.g. `prose-quality`, `heading-case`):

```yaml
lint_ignore:
- heading-case
```

Only **warnings** can be suppressed — errors always fire. The suppression is **gated on git**: it applies only while the page is **committed and clean**. A page with uncommitted changes (modified, staged, or untracked) still emits all its warnings. Two consequences follow by design:

- **The opt-out must be committed to take effect.** Adding `lint_ignore` makes the page dirty, so the warning keeps showing until you commit the change — i.e. you have to commit the decision before it counts.
- **Editing a suppressed page re-surfaces the rule.** As soon as you touch the page again, its warnings come back so you reconsider them against the new content, then go quiet once you re-commit.

Use it for warnings you've deliberately judged not to apply — e.g. a page carries `lint_ignore: [heading-case]` when a heading quotes a name that must keep its case. Dirtiness is detected via `git status`; outside a git repo (or if git is unavailable) nothing is considered dirty, so suppressions simply apply.

Python code is linted with ruff: `uv run ruff check scripts/ tests/`. Config lives in `pyproject.toml`.

### Show in browser

At any point during any skill, the developer can say "show in browser" to open the relevant wiki page in the **wiki-viewer** app (Next.js, in-repo at `wiki-viewer/`, `http://localhost:4777`). Check health first; launch detached only if it is not running:

```bash
curl -sf http://localhost:4777/api/index >/dev/null || {
  (cd wiki-viewer && setsid -f npm run dev >/dev/null 2>&1 < /dev/null)
  for i in $(seq 1 30); do curl -sf http://localhost:4777/api/index >/dev/null && break; sleep 0.5; done
}
```

Then open pages by wiki key (without `.md`):

```bash
xdg-open "http://localhost:4777/wiki/<key>"
```

The viewer reads pages straight off `wiki/` and resolves the same absolute `[[topic/slug]]` wikilinks Obsidian uses. Obsidian remains installed but is used **only by `/canvas`** (`.canvas` files have no browser equivalent); its socket-check launch flow lives in that skill.

Open the dashboard itself (`xdg-open "http://localhost:4777/"`) when you want the developer browsing rather than reading one page — its **Last studied** list ranks the pages behind the last 100 reviewed cards, most recent first, then by how many of those cards a page covers.

### Omvida (desktop app)

`~/Code/omvida` is a Quickshell app over the same wiki and deck: the wiki reader (tree, context panel, links, local graph), the deck explorer, the full graph, search with an "Ask Claude" that runs the [Query Protocol](#query-protocol) headless, and a **study loop** for typing answers. Each answer is graded by `claude -p` (flashcard-mcp `src/core/grading.ts`, fixed rubric) and the developer accepts or overrides the suggested rating with keys (Shift+Enter reveal, Alt+Enter accept, Shift+1-4 rate). It keeps `/study`'s session around the loop: Anki sync before and after, the pressure and calibration verdicts, leech blocking, the related-pages offer, and a `## Session N — Study` entry in today's log with `**Surface:** Omvida app`. Its Discuss, Add → Flashcards and Add → Wiki entry open Claude Code in kitty in this repo with the matching skill. Launch it with `~/Code/omvida/bin/omvida`, or `omvida open <wiki-key>` for a page ("show in Omvida", see the wiki-write protocol). The wiki-viewer stays; Omvida is a second surface over the same files.

### Flashcards in the viewer

The viewer reads flashcards **straight from flashcard-mcp's SQLite file** (`$FLASHCARD_MCP_DIR/prisma/master.db`, see [Machine-local configuration](#machine-local-configuration)) via `node:sqlite`, opened **read-only** — the MCP server owns all writes, and an accidental write here would corrupt review history that Anki sync treats as append-only. Override the file directly with `FLASHCARD_DB`. Two surfaces:

- **Per page** — a button in the article header opens a large modal with the page's cards, in two modes: an **overview** grid (fronts, answers revealed individually) and **flip-through** (one card at a time, 3D flip on click/space, arrow keys, progress bar). Cards come from the page's `flashcard_ids`; a page without any falls back to tag overlap.
- **Whole deck** — `/flashcards` (sidebar card icon) browses everything: true retention over a trailing 30 days with the calibration verdict, a clickable state bar (new / learning / review / relearning / suspended) that filters the list, plus deck, tag, and text filters, and the same flip-through over whatever the filters leave.

Retention is **not** recomputed in the viewer — `/flashcards` shells out to flashcard-mcp's CLI (`npm run dev:cli -- calibration`, ~0.5s) and renders the verdict it returns, so the browser and `/study` can never disagree. An earlier reimplementation drifted within a day (wrong min-review floor, no rating-discrimination guard, UTC instead of local days), which is why the rule has exactly one home. Retune bands in `src/core/calibration.ts` alone.

### Hiding non-wiki content

The vault is the whole repo, but only `wiki/` is knowledge content. Hiding the rest takes **two layers**, because Obsidian's core "Excluded files" setting only *dims* explorer entries — it never removes them:

| Surface | Mechanism | File |
| --- | --- | --- |
| Search, graph, quick-switcher, link autocomplete | `userIgnoreFilters` (core "Excluded files") | `.obsidian/app.json` |
| File-explorer sidebar (full removal) | CSS snippet using `.nav-folder:has(...)` / `.nav-file:has(...)` rules | `.obsidian/snippets/hide-non-wiki.css` (enabled via `enabledCssSnippets` in `.obsidian/appearance.json`) |

Both lists must stay **in sync**. Currently hidden: `scripts/`, `tests/`, `wiki-viewer/`, `CLAUDE.md`. Kept visible on purpose: `wiki/`, `logs/`, `AGENTS.md`, `todo.md`. Dotfolders (`.claude/`, `.git/`, `.venv/`, `.pytest_cache/`) are auto-ignored by Obsidian; non-markdown (`pyproject.toml`, `uv.lock`) is hidden by `showUnsupportedFiles: false`. The graph view is separately scoped to `path:wiki/ -path:wiki/indexes` via `.obsidian/graph.json`.

To change what's hidden: edit the list in **both** `app.json` (`userIgnoreFilters`) and `hide-non-wiki.css`, then reload Obsidian (`Ctrl+R`). For a folder, add `.nav-folder:has(> .nav-folder-title[data-path="<name>"])`; for a file, `.nav-file:has(> .nav-file-title[data-path="<name>.md"])`.

## Workflows

`.claude/workflows/*.js` are reusable multi-agent workflow definitions invoked via the **Workflow tool** (background, deterministic fan-out + synthesis). A skill instructing you to call one IS the opt-in — no separate confirmation needed.

- `research-grounding` — two-lane research for `/study-walkthrough` (and reusable standalone). The **authoritative lane** (docs/RFC/source agents) establishes facts; the **practitioner lane** (blog/talk/forum agents) gathers opinion (tradeoffs, lived experience, architectural nuance, gotchas). A synthesis agent reconciles them under a hard rule — **authoritative wins for facts** — flagging any practitioner claim that contradicts ground truth and keeping opinions labelled `consensus`/`contested`/`single-voice`, never promoted to facts. `args: { topic, cadence?, thoroughness?, fromUrl? }`; fan-out is `2+2+1` by default, `1+1+1` on concise/refresh, `3+3+1` on `thoroughness: deep`. When the workflow cannot run, the walkthrough falls back to a single background research subagent.

## Query Protocol

When the developer asks a substantive knowledge question — any "what is X / how does X work / why does X" or equivalent — handle it through this flow. The guiding principle: **never block the first answer on lookups**. Answer from memory immediately; run saved-knowledge lookups in the background and reconcile afterward.

1. **Answer first, from memory.** Give the developer your best answer right away based on your own knowledge. Do not run `mcp__qmd__query`, `mcp__flashcard-mcp__search_cards`, or any other lookup before this first response — those add latency (model inference, web round-trip) and would block the reply.

2. **Spawn one background subagent to do all lookup + verification + logging in parallel.** Immediately after (or alongside) the first answer, launch a single background agent (`run_in_background: true`) with a prompt that instructs it to:
   - Call `mcp__qmd__query` (hybrid BM25 + vector, `rerank: false`) and collect top hits.
   - Call `mcp__flashcard-mcp__search_cards` with the same query.
   - Optionally glance at `wiki/.wiki-index.json` sections/aliases if phrasing is unlikely to embed well.
   - **Always verify the memory answer against the web** via `WebSearch` (and `WebFetch` on the most authoritative result — official docs, source code, RFC, upstream repo — when the question has a specific factual claim to check). This runs regardless of whether wiki/cards hit, so memory answers are never trusted on their own.
   - Append a `## Query N (HH:MM)` entry to today's `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder; creating the file if missing) with: **Question**, **Wiki hits** (wikilinks or `none`), **Card hits** (ids + one-line fronts or `none`), **Web check** (one-line verdict: `confirms` | `contradicts: <what>` | `refines: <what>` | `inconclusive`, plus the authoritative URL used), **Source** (`wiki` | `cards` | `research` | `mixed` | `memory`), **Answer** (one-line summary of what you told the developer).
   - Report back the wiki/card hits **and the web-check verdict** so the main thread can reconcile.

   The main thread must not `Read` or `Write` the log file itself, and must not call `mcp__qmd__query` / `search_cards` directly. Same rule for the wiki-write follow-up when the developer accepts a `/study-walkthrough --write` offer: spawn it in the background.

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

Daily append-only logs live at **`logs/MM/YYYY-MM-DD.md`** — the parent folder is the zero-padded month (`logs/04/2026-04-30.md`, `logs/05/2026-05-30.md`). Each session records: skill used, topic, cards reviewed/created, accuracy, lapses, wiki updates, duration.

**Path convention (writing & reading):**
- **Today's log:** `logs/<MM>/<YYYY-MM-DD>.md`, where `<MM>` is the current month zero-padded. Create the month folder if missing.
- **A specific day** (e.g. yesterday, for a re-entry hint): derive `<MM>` from that day's date — it may differ from today's at a month boundary.
- **A window of days** (e.g. `/progress`): glob `logs/*/*.md` and filter by the `YYYY-MM-DD` date in the filename; do not assume a single month folder.
- A new daily log starts with a `# <YYYY-MM-DD>` header; session entries append below it.

**Section legend** (entries append at H2; `N` increments across ALL session types within a day; queries use their own sequence):
- `## Session N — Kickoff (HH:MM)`
- `## Session N — Study | Walkthrough | Flashcard | Reflection | Progression (HH:MM)`
- `## Session N — Change (HH:MM)` → **Files:** / **Change:** / **Why:**
- `## Session N — End (HH:MM)`
- `## Query N (HH:MM)` → Question / Wiki hits / Card hits / Web check / Source / Answer

**Always log repo changes.** Any change you make to this repo — skills, scripts, wiki, todo, config, AGENTS.md itself — must be recorded in today's `logs/<MM>/<YYYY-MM-DD>.md` as a `## Session N — Change (HH:MM)` entry with **Files:**, **Change:**, and **Why:** fields. Do this even outside a kickoff/end ritual. If today's log doesn't exist yet, create it with a `# <YYYY-MM-DD>` header.

## Anki Sync

`scripts/anki-sync` (module `scripts/ankisync/`) mirrors flashcard-mcp's cards to AnkiWeb so they can be reviewed on the phone. It is **stateless**: no sync bookkeeping exists anywhere — every run derives its plan from the current state of both sides.

- **Identity:** the Anki note `guid` is set to the master card's CUID. A note with a CUID-shaped guid but no master card is **imported**, because that is what a card created on another machine looks like; non-CUID guids are reported as unknown and never touched or imported.
- **Existence & content:** content is a one-way push, master.db always wins (front/back/tags/deck overwritten on any difference; Anki-side edits do not survive). Existence is **shared across machines**, since several of them sync through one AnkiWeb collection.
- **Deletion is explicit state, never absence.** Absence is ambiguous in both directions: a note missing from Anki is either brand new here or deleted elsewhere, and a card missing from master is either never seen here or deleted here. Guessing either way destroys cards, which it did — a sync on this machine deleted 8 cards that another machine had created (2026-09-16). So `delete_card` writes a `DeletedCard` tombstone row instead of just dropping the card, and the sync marks the Anki note with the `__deleted__` tag and suspends it instead of removing it. The tagged note is how the deletion reaches the other machines. Full table, `local \ remote`:

  | | LIVE (note) | DEL (tagged) | NONE |
  | --- | --- | --- | --- |
  | **LIVE** (row) | content + sched | soft-delete here | create on Anki |
  | **TOMB** (tombstone) | tag the note | nothing | nothing |
  | **NONE** | import | tombstone here | nothing |

  Two consequences: deleting a card **on the phone still does not delete it** (LIVE × NONE means "new here"), so the next sync recreates it and says so — `create N (M deleted on Anki, reinstated)`; and deleting it in master propagates everywhere and stays deleted. Tombstones and tagged notes are kept forever, and there is deliberately no command to purge them: a row is ~40 bytes, a suspended note never enters review, and no stateless run can know that every machine has processed the deletion. Clearing one early resurrects the card.
- **Scheduling:** flows both ways — the side with the newer last review wins its whole FSRS block (`stability`/`difficulty` map natively to Anki's `memory_state`; no SM-2 conversion). Anki-side recency comes from the newest **revlog** entry, never from `card.last_review_time`: a sync-down delivers a remote review as a revlog row without setting that field, and a push overwrites it from master, so it reads null or stale on exactly the cards Anki reviewed most recently. That field is a fallback only for cards with no revlog at all (an `inheritFrom` split carries a schedule but no reviews of its own), which is what stops those re-pushing on every run. Reviewing the **same card on both sides** between syncs is lossy by design: the newer side wins wholesale, and the loser's review survives in the history union but not in the block.
- **Review history:** append-only union by (card, timestamp) — phone reviews land in the `Review` table, local reviews land in Anki's revlog. Nothing is overwritten.
- **Bridge collection:** a dedicated headless Anki profile `StudySync` (`~/.local/share/Anki2/StudySync/`) — never the desktop profile. It is disposable: deleting the folder and re-running `sync` rebuilds it.
- **Credentials:** AnkiWeb email in `StudySync/sync-config.json` (via `anki-sync login <email>`); password in the GNOME keyring (`secret-tool store --label="AnkiWeb study sync" service ankiweb` — run by the developer, never via a skill). After first login the session token persists in the profile; the keyring is only read for re-auth.
- **Skill hooks:** `/study` runs `sync` before the pressure check (pull phone reviews first) and after the session log (push); `/study-flashcard` runs it after card creation. Always silent, one-line summary only when something moved; failures are a one-line note and never block the session.
- **Card content format:** Anki renders note fields as HTML, so card fronts/backs are authored in simple HTML (`<br>`, `<code>`, `<pre>`, `<b>`, `<i>`, `<ul>/<ol>/<li>`, entities for literal `<`/`>`) — never markdown, bare newlines, `[[wikilinks]]`, or em dashes (write two sentences instead). Enforced at write time: flashcard-mcp's `create_card`/`update_card` reject violations with a per-field error (`src/core/content-rules.ts`). See "Card Content Format" in `.claude/skills/study-flashcard/SKILL.md`; `scripts/card-htmlize` converts stragglers.

**Card size and scope are enforced too.** The same `content-rules.ts` caps the **answer at 200 visible characters and 4 sentences**, and requires the **front to ask one question**. Both limits measure rendered text, so markup and entities are free and formatting a card well never costs it budget; fronts carry no length cap, because grounded scenario fronts are the preferred style. The rejection message names the field and states both remedies (split the card, or reduce the text). The one-question check is a heuristic — 2+ question marks, or `and`/`or` followed by a question word, with `<code>` spans neutralised so a Ruby `nil?` is not miscounted — so it flags and the calling skill judges. The standing preference on a rejection is **reduce first**: splitting adds review load, and most violations are padding rather than two ideas. See "Card Size & Scope" in `.claude/skills/study-flashcard/SKILL.md`.

## Machine-local configuration

The flashcard-mcp checkout sits at a different path on each machine this repo is synced to, so **that path is never committed**. It is set once in `.env.local` at the repo root (gitignored; `.env.local.example` is the tracked template):

```sh
FLASHCARD_MCP_DIR=/home/felix/Code/Misc/flashcard-mcp
```

Changing that one line is the whole setup step on a new machine. `$HOME/...` and `~/...` are expanded. Three readers derive everything else from it, each parsing the file itself rather than sharing a loader:

| Reader | Resolves |
|---|---|
| `scripts/flashcard-mcp-server` (POSIX sh) | the `.mcp.json` command — execs `npx tsx $FLASHCARD_MCP_DIR/src/mcp/server.ts` with `DATABASE_URL` set. Writes only to stderr, since stdout is the MCP stdio stream |
| `scripts/config.py` | `flashcard_mcp_dir()` / `master_db()` for `scripts/ankisync` and `scripts/card-htmlize` |
| `wiki-viewer/lib/flashcard-path.ts` | `REPO_ROOT` (walks up to `AGENTS.md`), `flashcardMcpDir()`, `masterDbPath()` |

Environment variables take precedence over the file: `FLASHCARD_MCP_DIR`, `FLASHCARD_MASTER_DB` / `FLASHCARD_DB` (point at the SQLite file directly), `WIKI_ROOT`.

**Never hardcode an absolute home path** in `.mcp.json`, `scripts/`, or `wiki-viewer/lib/` — it breaks the other machine on the next pull, which has already happened twice. `tests/test_config.py::test_no_machine_specific_path_is_committed` fails on any `/home/<user>/…flashcard-mcp` literal in those files. When the config is absent, every entry point exits with a message naming `.env.local` instead of silently reading a nonexistent path.

## MCP Server

The `flashcard-mcp` MCP server must be running. It starts automatically via `.mcp.json`, whose `command` is the repo-relative `scripts/flashcard-mcp-server` launcher (project-scoped stdio servers spawn with the project root as cwd), which reads `FLASHCARD_MCP_DIR` as above.

If tools aren't available: check `.env.local` points at a real checkout, and that it has dependencies installed (`npm install` in that directory). Running `scripts/flashcard-mcp-server </dev/null` surfaces the path error directly.

**Calibration and leeches live in the MCP too.** `check_calibration` returns true retention over a trailing 30 days plus a verdict (`over-difficult` / `calibrated` / `under-difficult` / `low-signal`, with a `marginal` flag near a band edge), and drives `/study`'s difficulty levers — never the rating rubric. Leeches are not surveyed up front: `get_next_card` stamps any card it serves at 5+ lapses and the next `get_next_card` **throws** until that card is rewritten (`update_card`, which also resets `lapses`), split, deleted, or explicitly kept via `resolve_leech(id, "defer")` — which stops blocking until the card lapses again. Suspend is deliberately not offered: it hides the card instead of fixing it.

**`check_pressure` is the SRS pressure source of truth**, and it lives in the MCP server rather than this repo — the verdict and the enforcement have to agree, so they share one implementation. Two axes: `flashcardsDue` (review backlog, excluding the new-card pool) warns at 20 / pauses at 50, and `newToday` (intake) warns at 5 / pauses at 10. The server **enforces** the pause itself: `create_card` throws for a fresh card while the verdict is `pause`. `update_card` and splits (`create_card` with `inheritFrom`) are always allowed, and a split off a studied card does not count as intake — under a backlog, fixing the deck you already carry is exactly the right move. (A split off a never-reviewed parent inherits no maturity, so it does count.) Skills read the verdict via `references/srs-pressure-check.md`; nothing recomputes it locally.

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
- `scripts/wiki-write <page>` — Update index, refresh qmd search index, run lint
- `scripts/wiki-reindex [--wiki-dir DIR]` — Rebuild `.wiki-index.json` from every page: drops fields the current schema no longer writes, prunes entries for deleted pages, and carries each page's `updated` stamp over (a reindex is a derive, not a write). Use after any index schema change
- `scripts/lint` — Check broken wikilinks, frontmatter, alias collisions
- `scripts/anki-sync <login|sync|status>` — Sync flashcards to AnkiWeb (see [Anki Sync](#anki-sync)). `sync --dry-run` previews, `--local` skips AnkiWeb
- `scripts/card-htmlize` — Convert markdown/plain card text in master.db to simple Anki HTML (dry-run by default, `--apply` writes after backing up master.db)
- `scripts/flashcard-mcp-server` — stdio launcher used by `.mcp.json`; not run by hand except to debug a path problem (see [Machine-local configuration](#machine-local-configuration))

Search is not a `scripts/` entry point — it's the `qmd` CLI / `mcp__qmd__query` MCP tool, see [Search](#search).

Python modules live in `scripts/wiki/`. The top-level scripts are thin entry points.

## Dependencies

- **qmd**: `npm install -g @tobilu/qmd` — local hybrid search engine (BM25 + vector + LLM re-rank) for the wiki. Models (embedding, reranking, query-expansion GGUFs, ~2GB total) download once via `qmd pull`, cached in `~/.cache/qmd/models/`. Exposes an MCP server (`qmd mcp`, registered in `.mcp.json`) and a CLI. Auto-detects GPU acceleration (Vulkan/CUDA/Metal) via `node-llama-cpp`, falling back to CPU.
- **wiki-viewer**: Next.js app in-repo at `wiki-viewer/` — the browser surface for wiki pages (`http://localhost:4777`, health at `/api/health`). Run `npm install` in `wiki-viewer/`, then `npm run dev` (binds 127.0.0.1). See [Show in browser](#show-in-browser) and [Flashcards in the viewer](#flashcards-in-the-viewer).
- **Obsidian**: used only by `/canvas` (`.canvas` editing). Installed from the Debian package at `/opt/Obsidian/obsidian`; official CLI (`obsidian`) at `~/.local/bin/obsidian`. Launch detached with `setsid -f /opt/Obsidian/obsidian >/dev/null 2>&1 < /dev/null`; open files with `obsidian open vault="study" file="<slug>"`.
