# Wiki Write Protocol

Shared protocol for all skills that write to the developer wiki. Include this reference in any skill that offers "write wiki".

## Prerequisites

- Wiki directory: `wiki/` (Obsidian vault root)
- Index file: `wiki/.wiki-index.json`
- Scripts: `scripts/wiki-write`, `scripts/lint`
- qmd: local hybrid search (BM25 + vector + rerank) via `mcp__qmd__query`, or the `qmd` CLI

## "Write Wiki" Flow

When the developer says "write wiki" (or "save to wiki", "add to wiki"):

### Step 1: Read Index

Read `wiki/.wiki-index.json`. This gives you all existing pages with titles, aliases, sections, tags, and flashcard_ids.

### Step 2: Check for Existing Page (Extend/Split)

Search the index for title/alias overlap with the current topic:

1. Check index entries for title or alias matches
2. Call `mcp__qmd__query` (hybrid, `rerank: false`) for keyword/semantic matches on `<topic>`

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

## Writing Style

Write short, concrete sentences in active voice. If a sentence feels long, cut it in half.

These rules are enforced by `scripts/lint`. **Internalize them before drafting** — fixing prose after the fact takes multiple passes touching every page. The lint catches all em-dashes (including in headings, link text, and list-item descriptions) and most prose-colons.

### The two rules that cause the most cleanup churn

**No em-dashes anywhere.** Not in prose, not in headings, not in link text, not in list-item descriptions, not in table cells. The lint regex is plain `—` and only strips fenced code blocks before scanning.

| ❌ wrong                              | ✅ right                                            | Why                                  |
| ------------------------------------- | --------------------------------------------------- | ------------------------------------ |
| `X validates the token — it raises`   | `X validates the token. It raises`                  | Split into sentences                 |
| `relationships hold pointers — `{type, id}` pairs` | `relationships hold pointers, i.e. `{type, id}` pairs` | Use comma + connector for asides     |
| `[[link]] — short description`        | `[[link]]: short description`                       | List-item: colon after link is OK    |
| `[md](url) — what this is`            | `[md](url): what this is`                           | Same: colon after markdown link OK   |
| `**bold term** — explanation`         | `**bold term**. Explanation`                        | Split, capitalize the next word      |
| `## Heading — qualifier`              | `## Heading: qualifier` or `## Heading, qualifier`  | Headings flagged like prose          |
| `[v1.1 — Errors](url)`                | `[v1.1, Errors](url)` or `[v1.1 spec, Errors](url)` | Em-dash inside link text is flagged  |

**No prose-colons as clause connectors.** A colon may introduce a code fence, list, table, blockquote, or image. A colon after a wikilink, markdown link, bold term, or inline-code term at the start of a list item is allowed (the lint strips these before scanning). Anywhere else, split into two sentences.

| ❌ wrong                                          | ✅ right                                          |
| ------------------------------------------------- | ------------------------------------------------- |
| `These together mean: clients reconstruct the graph` | `These together mean clients reconstruct the graph` |
| `The trap: in one document, you cannot say X`     | `The trap. In one document, you cannot say X.`    |
| `The general principle: operations belong in...`  | `The general principle. Operations belong in...`  |
| `The litmus test: a generic client must work`     | `The litmus test. A generic client must work.`    |
| `A common temptation: "this should hide X"`       | `Consider this temptation. "This should hide X"`  |
| `Ask: does this have identity?`                   | `Ask whether the data has identity.`              |

**Allowed colon patterns (no flag):**

- `- [[wiki/page]]: description` (list item, colon after wikilink)
- `- [Title](url): description` (list item, colon after markdown link)
- `- **Term**: definition` (list item, colon after bold term)
- `- `code`: description` (list item, colon after inline code)
- End of line, before a fenced code block / list / table / blockquote / image
- Heading text: not flagged for colons (em-dashes still are)

### Headings are Title Case

Capitalize every word except articles, coordinating conjunctions, and short prepositions (`a`, `an`, `the`, `and`, `but`, `or`, `for`, `of`, `to`, `in`, `on`, `at`, `by`, `with`, `from`, `vs`, ...). Capitalize the first word after a colon. Lint check: `heading-case`.

Two rules override the casing, because headings routinely start with code:

- **The first word keeps whatever case you wrote.** `## not as a Filter` and `## on_delete vs dependent` stay as-is, since Title Case would otherwise capitalize a case-sensitive identifier.
- **Identifiers are never recased.** Anything in backticks, containing `_ ( ) . / @ #` or a digit, written in ALL CAPS, or carrying internal capitals is left verbatim: `` `delegated_type` ``, `inject()`, `Zone.js`, `NG0203`, `strictNullChecks`.

Bare identifiers that read as ordinary words (`included`, `dependent`, `scope`, `namespace`, `module`) are also preserved. If a new one bites, add it to `KEEP_VERBATIM` in `scripts/wiki/headings.py` rather than reworking the heading.

| ❌ wrong                                 | ✅ right                                  |
| ---------------------------------------- | ----------------------------------------- |
| `## two orthogonal axes`                 | `## Two Orthogonal Axes`                  |
| `## Case Study: the CPython chain`       | `## Case Study: The CPython Chain`        |
| `## Tradeoffs & gotchas`                 | `## Tradeoffs & Gotchas`                  |
| `## depth-first post-order traversal`    | `## Depth-First Post-Order Traversal`     |

### Other banned patterns (full list)

- **in order to** → `to`
- **it's worth noting / it should be noted** → delete; state directly
- **due to the fact that** → `because`
- **furthermore / moreover / additionally / notably / essentially** (line-leading) → cut or restructure
- **in conclusion** → cut
- **utilize / utilizes / utilized** → `use`
- **leverage(s|d) (verb)** → `use`
- **delve** → `explore` or `read`
- **is able to / has the ability to** → `can`
- **seamlessly** → delete or be specific
- **robust / comprehensive / holistic** → name the actual property
- **cutting-edge** → name the technology
- **harness (verb)** → `use`
- **that being said / it goes without saying** → cut

### Before / after (full sentences)

❌ `It is worth noting that in order to utilize the connection pool, you need to configure the pool size — this is done in database.yml.`

✅ `To use the connection pool, set the pool size in database.yml.`

---

❌ `ActiveRecord leverages lazy evaluation seamlessly, meaning the query is not executed until the results are needed — this is known as deferred execution.`

✅ `ActiveRecord defers query execution until results are needed. This is called lazy evaluation.`

---

When in doubt, cut the sentence in half.

### Bulk prose cleanup (when it slips through)

If lint flags many em-dashes or prose-colons after writing, do the cleanup in **one tool only**. The `Edit` tool errors with "File has been modified since read" if a Python script touched the file in the same session. Pick one path:

- **Python script** (preferred for >5 replacements across multiple files): one pass with all replacements, then re-run `scripts/wiki-write` to refresh embeddings.
- **Edit tool** (preferred for ≤5 replacements in one file): use `replace_all=true` for repeated patterns.

Do not intermix.

### Step 4: Generate Aliases

Generate 2-5 aliases for the page — common alternative names, abbreviations, alternate phrasings. Check each alias against the index to avoid collisions. Do not use single-letter abbreviations (lint enforces this as `alias-too-short`).

### Step 5: Resolve Links

Three sources of links, in order:

1. **Exact match**: Scan the draft content for any existing page title or alias from the index. Wrap matches in `[[absolute/path]]` format. Always use absolute paths from wiki root.
2. **qmd**: Call `mcp__qmd__query` (hybrid, `rerank: false`) with `<key concepts>` to find related pages. Present top hits to the developer: "These pages seem related — want to link any?"
3. **Walkthrough links**: Concepts discussed during the interactive session that the developer already confirmed as related — include these as links.

All wikilinks MUST use absolute paths: `[[architecture/cqrs]]` not `[[cqrs]]`.

### Step 6: Propose Folder

Infer the folder from tags and existing wiki structure:
- Check existing top-level folders in `wiki/`
- **If a top-level match exists, also check for a matching sub-folder**: for each tag on the new page, test whether `wiki/<folder>/<tag>/` exists. If it does, propose the sub-folder (`wiki/rails/routing/`) instead of the top-level (`wiki/rails/`).
- Propose: "I'd put this in `wiki/architecture/`. OK?" (or `wiki/rails/routing/` when a sub-folder matches)
- Developer confirms or overrides
- Create the folder if it doesn't exist: `mkdir -p wiki/<folder>/`
- Make sure the page's tags name its folder (and sub-folder): see "Topics" below.

### Step 7: Write File

Write to `wiki/<folder>/<slug>.md` where slug is the slugified title (lowercase, hyphens, no special chars).

**Filename MUST equal `slugify(title)` exactly.** This is a lint error (`slug-mismatch`), not a warning. The slugify rule lowercases, replaces non-alphanumeric runs with hyphens, and strips leading/trailing hyphens.

| Title                                          | Required filename                                  |
| ---------------------------------------------- | -------------------------------------------------- |
| `Document structure`                           | `document-structure.md`                            |
| `JSON:API document structure`                  | `json-api-document-structure.md` ← note the prefix |
| `meta vs resource`                             | `meta-vs-resource.md`                              |
| `meta vs resource — what belongs where`        | `meta-vs-resource-what-belongs-where.md` (also: drop the em-dash from titles) |

**Picking a title when the folder name disambiguates:** when the page lives in `wiki/json-api/`, the title does not need to repeat `JSON:API` — `Document structure` is sufficient and produces the cleaner filename. Repeat the topic in the title only when the page might be encountered without folder context (e.g., a deeply linked page or one that may move).

**Scaffold from the filename, not the other way around.** Decide the filename first (e.g., `query-conventions.md`), then set the title to a phrase that slugifies back to it (`Query conventions`).

### Step 8: Run Write Script

```bash
scripts/wiki-write wiki/<folder>/<slug>.md
```

This updates the index, refreshes the qmd search index (`qmd update` + `qmd embed`), and runs lint.

Parse the JSON output:
- `{"status":"ok","lint":"clean"}` → report success
- `{"status":"ok","lint":"warnings","details":"..."}` → write succeeded; surface warnings (e.g., prose quality) so the developer can decide whether to fix them
- `{"status":"ok","lint":"errors","details":"..."}` → show lint errors to developer (these block a clean write)

### Step 9: Append Session Log

Append to `logs/<MM>/<YYYY-MM-DD>.md` (zero-padded month folder; create if doesn't exist):

```markdown
## Session N — <Skill Name> (HH:MM)
- **Topic:** <topic>
- **Wiki updates:** [[folder/page-name]] created|extended
- **Links added:** [[folder/other-page]], [[folder/another]]
- **Flashcard IDs:** 123, 456 (if applicable)
```

### Step 10: Report Result

Tell the developer:
> Written `[[architecture/event-sourcing]]` with 3 links. Lint: clean.
> Session logged to `logs/04/2026-04-09.md`.

## "Show in browser" Flow

At any point during any skill, the developer can say "show in browser", "open in browser", or "present it". The skill should:

1. **Ensure the wiki-viewer is running** (launch detached only if health check fails):
   ```bash
   curl -sf http://localhost:4777/api/index >/dev/null || {
     (cd wiki-viewer && setsid -f npm run dev >/dev/null 2>&1 < /dev/null)
     for i in $(seq 1 30); do curl -sf http://localhost:4777/api/index >/dev/null && break; sleep 0.5; done
   }
   ```
   The wiki-viewer is the in-repo Next.js app at `wiki-viewer/` (binds `127.0.0.1:4777`).

2. **Open the relevant page by wiki key:**
   ```bash
   xdg-open "http://localhost:4777/wiki/<key>"
   ```
   Use the wiki-relative key without `.md` (e.g. `git/git-restore`, `security/hsts`).

4. **Resume the skill session** — this is a non-blocking side action, not a skill interruption.

**"Show in Omvida"** is the same, in the Omvida desktop app (`~/Code/omvida`) instead of the browser: one command, no server to start. It opens the page in the running Omvida, or starts one:
```bash
~/Code/omvida/bin/omvida open <key>
```
Use it when the developer says "show in Omvida" or "open in the app"; "show in browser" keeps meaning the wiki-viewer.

## Topics

A topic is a folder and a tag, not a page. There are no index or map-of-content pages: the folder tree in the wiki-viewer and Omvida lists every page, and the graph shows how they connect.

- Tag every page with its folder name, and with its sub-folder name when it sits in one (`tags: [rails, routing, ...]`), plus the subject tags it shares with pages elsewhere (`api-design`, `security`).
- Tags are what holds a topic together without links: the graph pulls pages that share a tag towards each other, and its "Around the open page" view includes pages that share a tag with the open one. A page with no shared tags and no links floats alone.
- One level of sub-folders is the maximum (`wiki/rails/routing/`). Split a folder by hand when one tag clusters many of its pages: `git mv` them into `wiki/<folder>/<tag>/`, rewrite their `[[<folder>/<slug>]]` wikilinks to `[[<folder>/<tag>/<slug>]]` everywhere, then re-run `scripts/wiki-write` on each page.
- Don't create a page whose only job is to list other pages.

## Linking Rules Summary

- All wikilinks use absolute paths from wiki root: `[[architecture/cqrs]]`
- Page filename = slugified title: lowercase, hyphens, no special chars
- Aliases declared in frontmatter, checked against index for uniqueness
- Obsidian resolves aliases automatically via frontmatter
- When extending a page, preserve existing links and add new ones
- Never create a broken link intentionally — if a target doesn't exist, either create a stub or don't link

## Frontmatter Required Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | Yes | Human-readable title |
| `aliases` | array | Yes | Alternative names for this concept |
| `tags` | array | Yes | Topic tags for organization |
| `created` | date | Yes | ISO date of creation |
| `updated` | date | Yes | ISO date of last update |
| `source_skill` | string | Yes | Which skill created this page |
| `flashcard_ids` | array | No | Associated SRS flashcard IDs. Auto-filled to `[]` by `scripts/wiki-write` if missing. Drives the wiki-viewer's per-page flashcard modal and `/study`'s post-session page suggestions, so keep it accurate when a page's cards change. |

**The schema is closed.** The table above plus `lint_ignore` is the complete set of permitted keys; `scripts/lint` reports anything else as a `forbidden-field` **error**. That includes the retired scheduling fields (`next_review`, `review_interval`, `last_deepened`) — wiki pages are not scheduled, only flashcards are studied — and earlier retirements like `depth`, `probe_sections` and `allow_orphan` (the orphan check went with the index pages). Adding a genuinely new field means adding it to `ALLOWED_FIELDS` in `scripts/wiki/lint.py` first.
