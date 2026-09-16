# Wiki Viewer — Design Contract

Local Next.js viewer for the study wiki at `/home/felix/Code/Misc/study/wiki` (env `WIKI_ROOT`).
Read this whole file before writing any code.

## The wiki being rendered

- ~66 markdown pages in topic folders, up to 3 levels deep (`rails/foreign-keys`, `rails/routing/scope-vs-namespace`).
- Every page has YAML frontmatter (title, aliases, tags, created, updated, source_skill, flashcard_ids). Pages are **not** scheduled — there is no review state on a page.
- Body is GitHub-flavored markdown: headings, tables, fenced code blocks (ruby/ts/sql/bash), blockquotes.
- Internal links are Obsidian wikilinks with **absolute paths**: `[[rails/foreign-keys]]`, optionally `[[path#Heading]]` and `[[path|display text]]`. Embeds `![[...]]` are rare and may be ignored.
- `*-index.md` pages are MOCs (maps of content) for their topic. They are NOT rendered as
  pages (folder views replace them): excluded from `pages`/tree/search/link lists, kept only
  as ghost nodes in the graph (translucent dashed; click opens the folder view). Wikilinks
  targeting a MOC resolve to its folder view via the `mocs` param of `createWikilinkResolver`.
- The wiki is **read-only** for this app; the viewer writes nothing anywhere.

## The flashcard deck

- `lib/flashcards.ts` reads flashcard-mcp's SQLite file directly (`FLASHCARD_DB`, default `~/Code/flashcard-mcp/prisma/master.db`) through `node:sqlite`, opened **read-only** — the MCP server owns writes.
- A page links to cards through its `flashcard_ids`; pages without any fall back to tag overlap.
- Surfaces: a per-page modal from the article header, and `/flashcards` for the whole deck (retention, state filters, tag/deck/text filters, flip-through).
- The calibration verdict is **not** computed here. `lib/calibration.ts` runs flashcard-mcp's `dev:cli calibration` and renders its JSON, so the viewer and `/study` always agree. Override the repo path with `FLASHCARD_MCP_DIR`.
- Datetime columns in master.db hold both epoch-ms integers and ISO text. Every read normalizes via the `epochMs` helper in `lib/flashcards.ts`; comparing such a column against a string silently drops ~75% of the rows.

## Stack (already installed — do not add dependencies)

Next 16.2 (App Router, **params are async** — `await params` in pages/routes), React 19.2, Tailwind v4, TypeScript.
Libraries: `gray-matter`, `react-markdown` + `remark-gfm` + `rehype-highlight`, `react-force-graph-2d`, `clsx`, `@tailwindcss/typography`.

**Do not guess library APIs.** Verify against the installed package (`node_modules/<pkg>/dist/index.d.ts`, README) before use.

## Foundation (already written — import, never modify)

- `lib/types.ts` — `PageMeta`, `TreeFolder`, `GraphNode`, `GraphLink`, `WikiIndexPayload`, `WikiPage`. Read it.
- `lib/wiki.ts` — server-only: `getWikiIndex()`, `getPage(path)`, `safeWikiFile(path)`, `WIKI_ROOT`.
- `lib/colors.ts` — `topicColor(folder)` → stable hex color per top-level topic. Use it everywhere a topic needs color (graph nodes, tag chips, tree accents).
- `components/providers/WikiDataProvider.tsx` — client: `useWikiData()` → `{ data: WikiIndexPayload | null, byPath: Map<string, PageMeta>, refresh }`; `useCurrentPagePath()` → wiki path or null. Data is null on first paint — render skeletons/empty states, never crash.
- `app/api/index/route.ts` — serves the payload.
- `app/layout.tsx` — composes: `Sidebar` (left) | scrollable `main` | right rail filled by `GraphPanel`. `CommandPalette` mounted globally. Already imports `highlight.js/styles/github-dark-dimmed.css`.
- `app/globals.css` — Tailwind v4 `@theme` tokens.

## Design language

Warm paper-white, calm reference-tool aesthetic (iA/Linear-light adjacent); depth via soft
shadows and white-on-paper layering, never heavy borders. Use ONLY the theme tokens via
Tailwind classes: `bg-bg`, `bg-panel`, `bg-panel-2`, `border-border`, `text-fg`, `text-muted`,
`text-faint`, `text-accent`, `bg-accent-soft`. Font classes `font-sans` / `font-mono`.
- Panels: `bg-panel` with `border-border` 1px separators. Radius `rounded-md`/`rounded-lg`. No shadows.
- Interactive rows: `text-muted hover:text-fg hover:bg-panel-2 rounded-md px-2 py-1 transition-colors`.
- Active/current item: `bg-accent-soft text-accent`.
- Section labels: `text-[11px] uppercase tracking-wider text-faint font-medium`.
- Tag chips: tiny rounded pills, `topicColor` at low opacity background.
- Keep everything dense and quiet; this is a daily tool, not a marketing page.

## Component contracts (exact export names/paths — layout imports them)

| File | Export | Notes |
| --- | --- | --- |
| `components/sidebar/Sidebar.tsx` | `export default function Sidebar()` | client |
| `components/graph/GraphPanel.tsx` | `export default function GraphPanel()` | client |
| `components/search/CommandPalette.tsx` | `export default function CommandPalette()` | client |
| `app/wiki/[...slug]/page.tsx` | default async page | server |
| `app/page.tsx` | default page | server or client |

Routing: page paths map to `/wiki/<path>` (e.g. `/wiki/rails/foreign-keys`). Use `next/link` for all internal navigation so client panels persist.

## File ownership (hard boundaries — never write outside your set)

- **article**: `app/wiki/[...slug]/page.tsx`, `components/article/**`, `lib/markdown.ts`
- **sidebar**: `components/sidebar/**`
- **graph**: `components/graph/**`
- **home**: `app/page.tsx`, `components/search/**`

(A per-page notes feature once owned `components/notes/**` + `/api/notes` — removed by request; the graph now gets the whole right rail.)

Shared files (`app/layout.tsx`, `app/globals.css`, `lib/types.ts`, `lib/wiki.ts`, `lib/colors.ts`, provider) are frozen. If you need a global style hook, use Tailwind utilities locally instead.

## Polish phase (applied after integration — explicit user requirements)

1. **Connections footer on every article — "where did I come from / where do I want to go?"**
   At the end of each article (after the body, before any page padding ends), a visually
   distinct two-column section, like a book's prev/next navigation but graph-shaped:
   - Left column **"← Linked from"** (inbound/backlinks = the pages you likely arrived from).
   - Right column **"Links to →"** (outbound = where to continue).
   Each entry is a quiet card row: page title (text-fg, medium), below it the top-level
   folder name with its `topicColor` dot (text-faint, 12px). Hover: `border-accent`-ish
   border tint + title to `text-accent`. Cards: `bg-panel border border-border rounded-lg
   px-4 py-3`, stacked with `gap-2`. Empty side: faint "nothing links here yet" / "no
   outgoing links". Columns stack on narrow widths. Separated from the body by a top
   border and a section label pair per the design language.

2. **Reading-first article design.** The article column is the hero: comfortable measure
   (~max-w-3xl), 17px body, relaxed leading (already in `.wiki-prose`), generous vertical
   padding (`py-12`+), quiet meta chrome (header badges small and faint, never competing
   with the text). Joy lives in the typography, not in decoration.
