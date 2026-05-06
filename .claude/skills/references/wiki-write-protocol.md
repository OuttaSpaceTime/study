# Wiki Write Protocol

Shared protocol for all skills that write to the developer wiki. Include this reference in any skill that offers "write wiki".

## Prerequisites

- Wiki directory: `wiki/` (Obsidian vault root)
- Index file: `wiki/.wiki-index.json`
- Scripts: `scripts/wiki-write`, `scripts/lint`, `scripts/wiki-search`
- TreeSearch: `treesearch` CLI (pytreesearch)
- Ollama: running locally with `nomic-embed-text` model

## "Write Wiki" Flow

When the developer says "write wiki" (or "save to wiki", "add to wiki"):

### Step 1: Read Index

Read `wiki/.wiki-index.json`. This gives you all existing pages with titles, aliases, sections, tags, and flashcard_ids.

### Step 2: Check for Existing Page (Extend/Split)

Search the index for title/alias overlap with the current topic:

1. Check index entries for title or alias matches
2. Run `treesearch search --query "<topic>" --index_dir wiki/indexes` for keyword matches
3. If Ollama is running, run `scripts/wiki-search "<topic>"` for semantic matches

If a match is found, show the developer:
> `architecture/event-sourcing` already exists with sections: Core Concepts, Projections, Related Concepts.
>
> Your walkthrough covered: event versioning, upcasting, schema evolution.
>
> **Extend** the existing page with new sections, or **split** into a new page?

Developer decides. If extending, read the existing file and add new H2 sections.

### Step 3: Draft Page Content

Draft the wiki page from the walkthrough content. Use this format:

```markdown
---
title: "Page Title"
aliases: [alias one, alias two]
tags: [topic-area, sub-topic]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_skill: study-flashcard|study|study-walkthrough
flashcard_ids: [cuid1abc, cuid2def]
next_review: YYYY-MM-DD
review_interval: 3
---

# Page Title

Opening paragraph explaining the concept.

## Section One

Content...

## Section Two

Content...

## Related Concepts

- [[folder/page-name]]: brief explanation of relationship
```

## Headings as SRS Prompts

H2 headings become `probe_sections` — the quiz question at review time. Write them specific enough to self-grade without re-reading the page.

- ❌ `## When to Use` → ✅ `## When to reach for pick over pluck`
- ❌ `## Gotchas` → ✅ `## nil on no match and chaining behavior`
- ❌ `## Overview` → ✅ `## What HSTS is and why the first visit is still vulnerable`

If the heading doesn't tell you what to recall, rename it before setting `probe_sections`.

## Writing Style

Write short, concrete sentences in active voice. If a sentence feels long, cut it in half.

**Common patterns to avoid:**

- **em dash connector**: ❌ `X validates the token — it raises if invalid` → ✅ `X validates the token. It raises if invalid.`
- **in order to**: ❌ `Call this in order to parse the response` → ✅ `Call this to parse the response`
- **it's worth noting / it should be noted**: ❌ `It's worth noting that indexes speed up reads` → ✅ `Indexes speed up reads`
- **utilize**: ❌ `The client utilizes a connection pool` → ✅ `The client uses a connection pool`
- **leverage (verb)**: ❌ `Rails leverages the database for locking` → ✅ `Rails uses the database for locking`
- **seamlessly**: ❌ `It integrates seamlessly with Rack` → ✅ `It integrates with Rack via the standard middleware interface`
- **in conclusion / additionally**: ❌ `Additionally, the cache is invalidated on write` → ✅ `The cache is invalidated on write`
- **is able to**: ❌ `The worker is able to process multiple queues` → ✅ `The worker can process multiple queues`

**Before / after (full sentences):**

❌ `It is worth noting that in order to utilize the connection pool, you need to configure the pool size — this is done in database.yml.`

✅ `To use the connection pool, set the pool size in database.yml.`

---

❌ `ActiveRecord leverages lazy evaluation seamlessly, meaning the query is not executed until the results are needed — this is known as deferred execution.`

✅ `ActiveRecord defers query execution until results are needed. This is called lazy evaluation.`

---

When in doubt, cut the sentence in half.

### Step 4: Generate Aliases

Generate 2-5 aliases for the page — common alternative names, abbreviations, alternate phrasings. Check each alias against the index to avoid collisions. Do not use single-letter abbreviations.

### Step 5: Resolve Links

Three sources of links, in order:

1. **Exact match**: Scan the draft content for any existing page title or alias from the index. Wrap matches in `[[absolute/path]]` format. Always use absolute paths from wiki root.
2. **TreeSearch**: Run `treesearch search --query "<key concepts>"` to find related pages. Present top hits to the developer: "These pages seem related — want to link any?"
3. **Walkthrough links**: Concepts discussed during the interactive session that the developer already confirmed as related — include these as links.

All wikilinks MUST use absolute paths: `[[architecture/cqrs]]` not `[[cqrs]]`.

### Step 6: Propose Folder

Infer the folder from tags and existing wiki structure:
- Check existing top-level folders in `wiki/`
- Propose: "I'd put this in `wiki/architecture/`. OK?"
- Developer confirms or overrides
- Create the folder if it doesn't exist: `mkdir -p wiki/<folder>/`
- If the proposed folder has no `<folder>-index.md` yet, offer to create the MOC page in the same step (see "MOC Pages" below).

### Step 7: Write File

Write to `wiki/<folder>/<slug>.md` where slug is the slugified title (lowercase, hyphens, no special chars).

### Step 8: Run Write Script

```bash
scripts/wiki-write wiki/<folder>/<slug>.md
```

This updates the index, reindexes TreeSearch, embeds via Ollama, and runs lint.

Parse the JSON output:
- `{"status":"ok","lint":"clean"}` → report success
- `{"status":"ok","lint":"warnings","details":"..."}` → write succeeded; surface warnings (e.g., orphan pages) so the developer can decide whether to add inbound links
- `{"status":"ok","lint":"errors","details":"..."}` → show lint errors to developer (these block a clean write)

### Step 8b: Update Depth Metadata (when extending)

If the page was extended by `/study-walkthrough`, increment the `depth` frontmatter field and set `last_deepened` to today's date. If the field doesn't exist, add `depth: 2` (the initial write was depth 1).

### Step 9: Append Session Log

Append to `logs/YYYY-MM-DD.md` (create if doesn't exist):

```markdown
## Session N — <Skill Name> (HH:MM)
- **Topic:** <topic>
- **Wiki updates:** [[folder/page-name]] created|extended (depth: 3)
- **Links added:** [[folder/other-page]], [[folder/another]]
- **Flashcard IDs:** 123, 456 (if applicable)
```

### Step 10: Report Result

Tell the developer:
> Written `[[architecture/event-sourcing]]` with 3 links. Lint: clean.
> Session logged to `logs/2026-04-09.md`.

## "Show in Obsidian" Flow

At any point during any skill, the developer can say "show in Obsidian", "open in Obsidian", or "present in Obsidian". The skill should:

1. **Launch Obsidian** (only if not already running):
   ```bash
   pgrep -f "obsidian" >/dev/null 2>&1 || (snap run obsidian &>/dev/null & disown && sleep 3)
   ```

2. **Open the relevant page by slug:**
   ```bash
   obsidian open vault="study" file="<slug>"
   ```
   Use the bare slug (e.g. `git-restore`, `hsts`) — `file=` resolves by name like wikilinks. Do NOT use `path=` (returns "File not found"). The vault name is `study`.

4. **Resume the skill session** — this is a non-blocking side action, not a skill interruption.

## MOC Pages

Every top-level wiki folder has a **MOC (Map of Content) page** — a hub that wikilinks every other page in the folder. This gives the Obsidian graph a clean hub-and-spoke shape per topic and provides a browsable index.

### Convention

- One MOC per top-level folder: `wiki/<folder>/<folder>-index.md` (e.g. `wiki/git/git-index.md`)
- Title: `"<Folder> Index"`, slug = `<folder>-index`, wikilink: `[[<folder>/<folder>-index]]`
- Only top-level folders get MOCs — nested folders do not.

### MOC frontmatter template

```yaml
---
title: "Git Index"
aliases: [git-moc, git map]
tags: [moc, git]
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_skill: manual
probe_sections: [Pages]
last_probed: [Pages]
allow_orphan: true
---

# Git Index

Map of content for the `git/` wiki folder. Auto-maintained by `scripts/wiki-write`.

## Pages

- [[git/git-restore]]
```

### Rules for MOC pages

- **Must include `tags: [moc, <folder>]`** — the `moc` tag is the exclusion marker; `scripts/wiki-due` and study-selection skips any entry tagged `moc`.
- **Must NOT include `next_review` / `review_interval`** — MOCs are hubs, not studyable content.
- **Must include `allow_orphan: true`** — MOCs have no inbound links by design.
- **Must NOT be created as flashcard sources** — do not pass them to `/study-flashcard`.

### Auto-maintenance

`scripts/wiki-write` **auto-rebuilds the `## Pages` section** of the folder's MOC every time any page in that folder is written. The rebuild is from the filesystem (sorted wikilinks to every non-MOC `*.md` in the folder), so:

- Skills writing a new page do **not** need to touch the MOC manually — it will be updated automatically.
- Deleted pages drop out on the next write in that folder.
- Manual edits to the `## Pages` section are overwritten on the next write; edit other sections freely.

If a folder has no MOC yet, `scripts/wiki-write` emits a stderr warning and the lint reports `moc-missing`. Create the MOC once using the template above, then run `scripts/wiki-write wiki/<folder>/<folder>-index.md`.

## Linking Rules Summary

- All wikilinks use absolute paths from wiki root: `[[architecture/cqrs]]`
- Page filename = slugified title: lowercase, hyphens, no special chars
- Aliases declared in frontmatter, checked against index for uniqueness
- Obsidian resolves aliases automatically via frontmatter
- When extending a page, preserve existing links and add new ones
- Never create orphan links intentionally — if a target doesn't exist, either create a stub or don't link

## Frontmatter Required Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Human-readable title |
| `aliases` | array | Yes | Alternative names for this concept |
| `tags` | array | Yes | Topic tags for organization |
| `created` | date | Yes | ISO date of creation |
| `updated` | date | Yes | ISO date of last update |
| `source_skill` | string | Yes | Which skill created this page |
| `flashcard_ids` | array | No | Associated SRS flashcard IDs |
| `depth` | number | No | How many times this page has been deepened (starts at 1, incremented by `/study-walkthrough`) |
| `last_deepened` | date | No | ISO date of last deepening session |
| `next_review` | date | No | ISO date of next scheduled review. Set to `created + 3 days` on page creation. Updated after each review by `/study`. |
| `review_interval` | number | No | Current review interval in days. Starts at 3. Updated after each review using spaced repetition scheduling. |
