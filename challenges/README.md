# Challenges

A challenge is a small interactive code exercise linked to one H2 section of one wiki page. It is the successor to the retired `probes/` concept: instead of committed command transcripts, a challenge is a live exercise the developer solves in the wiki-viewer browser app (`http://localhost:4777/study/<id>`), where the run output is its own ground truth.

## The atomic principle

Challenges follow the flashcard rule: **one idea per challenge, minimal and self-contained, no overhead**. A stub is a few lines with one missing piece, not a program. If a challenge needs multi-file scaffolding, imports beyond the standard toolkit of its env, or setup prose longer than its code, it has outgrown this folder. Split it, shrink it, or link the wiki page to a real project under `~/Code` instead.

## Structure

```
challenges/
  <topic>/<slug>.md      permanent challenges, linked to a wiki page + section
  scratch/               ad-hoc probing challenges written during walkthroughs
  _template.md           copy to start a new challenge (skipped by tooling)
  envs.json              execution environment registry (shared with wiki-viewer)
  envs/<id>/             optional committed project envs (artifacts gitignored)
  .attempts/             attempt state written by the viewer (gitignored)
```

The challenge **id** is the path relative to this folder without `.md`, always two segments: `security/hsts-preload`, `scratch/2026-07-03-1430-closures`.

## Frontmatter

| Field | Required | Meaning |
| --- | --- | --- |
| `wiki` | permanent only | Wiki key of the linked page (`security/hsts`, no `.md`) |
| `section` | permanent only | Exact H2 text; matched normalized (case and trailing punctuation ignored) |
| `kind` | yes | `write-code` (fill in the stub) or `predict-output` (read code, predict stdout) |
| `env` | yes | Key into `envs.json` |
| `questions` | yes | 1-2 questions about the section, answered in chat at review time |
| `created` | yes | ISO date |

One challenge max per (wiki page, section). Scratch challenges skip `wiki`/`section` but still need a known `env`.

Lint enforces: `challenge-wiki-missing`, `challenge-wiki-unresolved`, `challenge-section-unresolved`, `challenge-duplicate-section`, `challenge-env-unknown` (all errors, via `scripts/lint`).

## Body sections

- `## Brief` — 1-3 sentences of context.
- `## Setup` — optional; `pg` env only: schema/seed SQL applied before the user's SQL.
- `## Stub` — the code shown in study mode, with the missing piece marked `TODO` (or the full code for `predict-output`).
- `## Solution` — full working code. Never sent to the browser in study mode.
- `## Expected Output` — optional; exact stdout of the solution. Required for `predict-output`. Captured from a real run, never hand-written.

Browser challenges (`web`/`react` envs) may carry multiple fences in Stub/Solution (`html`, `css`, `js`, or one `jsx`); they render in a sandboxed iframe instead of running server-side.

## Environments

`envs.json` pins every runtime to an absolute interpreter path or project directory; the viewer executes only what the registry defines, never anything from the request. Three tiers, in order of preference:

1. **Inline** (`python312`, `node24`, `ts-node24`, `ruby`) — code runs as a single temp file against a pinned interpreter. The default; keeps challenges atomic.
2. **Project** (`rails`) — code runs inside a background project (`bin/rails runner` in the study-challenges sandbox). Use only when the framework itself is the topic.
3. **Service** (`pg`) — SQL runs against a throwaway database on the dedicated `study-pg` Docker container (port 55432); `## Setup` seeds it, the database is dropped after the run.

Value schema: `{ type: "inline"|"project"|"postgres"|"browser", command?: [argv with {file}], ext?, cwd?, timeoutMs?, preset? }`. The registry is a shared contract with wiki-viewer; study-side lint checks key existence only.

## Attempts

The viewer writes `challenges/.attempts/<topic>/<slug>.json` on every run: `{ id, kind, env, code, files, predictedOutput, output, exitCode, timedOut, status, runCount, updatedAt }`. `/study` reads this file when the developer says "challenge finished" to evaluate the attempt together with the question answers. Never committed.

## Linking

The wiki→challenge link lives on the challenge (`wiki:` + `section:`), one-way and derived, so wiki pages stay clean and the link is always fresh. Look up challenges with `scripts/challenges <wiki-key>` (add `--section "<h2>"` for one section, `--scratch` for scratch, `--count` for counts). The `probe_sections`/`last_probed` frontmatter on wiki pages is the unrelated SRS review rotation and keeps its name.
