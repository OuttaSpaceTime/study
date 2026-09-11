# study

A personal learning workspace: a developer wiki, a spaced-repetition flashcard loop, and
the session logs that connect them. The repo root doubles as an Obsidian vault.

The idea borrows from the [Karpathy LLM wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
pattern with one deliberate constraint — **content only enters through an interactive skill,
never bulk ingestion.** Nothing is written to the wiki that wasn't worked through first.

## What's here

| Path | What it is |
|---|---|
| `wiki/` | 67 pages of technical notes, organised by topic (`rails/`, `typescript/`, `security/`, `sql/`, `angular/`, `software-design/`, …) |
| `logs/` | 72 dated session logs — what was studied, what lapsed, which cards were split and why |
| `wiki-viewer/` | Next.js app for browsing the wiki and the flashcard deck |
| `scripts/` | Python tooling, chiefly `ankisync` for pushing cards to Anki |
| `canvases/` | Obsidian canvases, e.g. a Pólya "How to Solve It" scaffold |
| `.claude/` | The skills that drive all of the above |

## How it works

Flashcards are the only thing reviewed on a schedule; wiki pages never become "due". A study
session runs the card loop first, then offers the pages connected to the cards actually
studied — matched on `flashcard_ids`, falling back to tag overlap. Cards are held in
[flashcard-mcp](https://github.com/OuttaSpaceTime/flashcard-mcp) and reached over MCP.

Every wiki page carries YAML frontmatter with a closed schema (`title`, `aliases`, `tags`,
`created`, `updated`, `source_skill`, `flashcard_ids`). `scripts/lint` rejects any key outside
it, so retired fields can't quietly reappear. Wikilinks are absolute from the wiki root —
`[[architecture/cqrs]]`, never `[[cqrs]]`.

The skills follow a few rules worth stating: no step may end in "go away and come back later",
the human drives every decision, and a correction edits the original statement rather than
appending a contradiction. `AGENTS.md` is the full operating schema.

## Setup

```bash
uv sync
npm --prefix wiki-viewer install
```

`scripts/lint` checks the wiki; `wiki-viewer` serves it.

## Note

Daily journal entries and the working todo list stay local — they're gitignored and were
removed from history.
