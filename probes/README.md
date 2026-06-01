# Probes

Small, read-only commands run during a `/study-walkthrough` (or `/study`) session to turn **Assumed** understanding into **Known** — the portable analog of Solveit's live Python kernel.

A probe is a scratch pad *and* a keepsake: the markdown file is where you draft the prediction, paste the command, capture the output, and jot the takeaway while working. Committed probes compound across sessions — future walkthroughs on the same topic read prior probes first.

## Structure

```
probes/
  <topic-slug>/
    YYYY-MM-DD-HHMM-<brief>.md
    ...
  _template.md
```

One file per probe. Topic slugs match wiki path tails where possible (`event-sourcing`, not `architecture-event-sourcing` — the folder does the namespacing).

## Format

Every probe file has four sections. Each section holds exactly one idea.

```markdown
---
topic: event-sourcing
session: 2026-04-21-walkthrough
wiki: architecture/event-sourcing
created: 2026-04-21 09:15
---

## Prediction
What I expect to happen, before running the command. One sentence.

## Command
​```bash
# The exact command, runnable as-is
​```

## Output
​```
# Captured verbatim. Trim to the relevant lines.
​```

## Takeaway
What the output changed about my understanding. One or two sentences. If the
prediction was wrong, say so explicitly — that's the load-bearing half.
```

## Rules

- **Read-only.** Probes never mutate production state, write to shared DBs, or change data the dev depends on. If a probe needs instrumentation (a `print`, a `console.log`), revert it in the same session.
- **Small.** One command. If you need a harness, the ambiguity is too big for a probe — walk the code instead.
- **Cited verbatim.** The command in the probe file is the exact thing that was run. Future-you re-runs it, compares output, and sees whether reality drifted.
- **Prediction first.** Write the Prediction section *before* running the command. Without a prediction, a probe is just a log — it doesn't teach anything.
- **Takeaway lands in the session log.** When the probe changes your understanding, mirror the Takeaway line into the `/study-walkthrough` session log's `Surprising:` or `Heuristic:` field so it's findable without grepping `probes/`.

## Dependencies

Most probes are one-liners against what's already installed (`git`, `curl`, stdlib). When a probe needs packages, escalate in tiers — do not reach for a heavier tool than the probe actually needs.

Python, JavaScript, and Ruby are all first-class. Pick the runtime that matches the thing being probed (or the thing being learned) — don't force Python when the concept is a Ruby gem.

### Tier 1 — inline (default)

The dep spec lives inside the command. The probe file is self-contained and re-runnable years later.

**Python** — `uv run --with <pkg>`:
```bash
uv run --with httpx python -c "import httpx; print(httpx.get('https://example.com').status_code)"
```

**JavaScript** — `npx <pkg>`, `bunx <pkg>`, or `node --input-type=module -e '...'` for stdlib:
```bash
npx --yes zx -e 'console.log(await $`git log --oneline -3`)'
```
```bash
node --input-type=module -e 'import fs from "node:fs"; console.log(fs.readdirSync("."))'
```

**Ruby** — `ruby -e '...'` for stdlib, or `bundler/inline` when a gem is needed:
```bash
ruby -e 'require "json"; puts JSON.parse(File.read("package.json"))["name"]'
```
```bash
ruby -e '
require "bundler/inline"
gemfile { source "https://rubygems.org"; gem "httparty" }
puts HTTParty.get("https://example.com").code
'
```

### Tier 2 — topic env (when deps start repeating)

When a topic folder accumulates **3+ probes sharing the same deps**, promote the shared env to the topic folder. Scaffold once, probes from then on `cd` into the folder.

**Python** — `probes/<topic>/pyproject.toml` (uv):
```bash
cd probes/event-sourcing && uv init --no-readme && uv add httpx
# then:
cd probes/event-sourcing && uv run python -c "..."
```
Commit `pyproject.toml` and `uv.lock`; gitignore `.venv/`.

**JavaScript** — `probes/<topic>/package.json` (npm, pnpm, or bun — pick one per topic):
```bash
cd probes/graphql-n-plus-1 && npm init -y && npm install graphql
# then:
cd probes/graphql-n-plus-1 && node -e "..."
```
Commit `package.json` and the lockfile (`package-lock.json` / `pnpm-lock.yaml` / `bun.lockb`); gitignore `node_modules/`.

**Ruby** — `probes/<topic>/Gemfile`:
```bash
cd probes/rails-cache-semantics && bundle init && bundle add httparty && bundle install --path vendor/bundle
# then:
cd probes/rails-cache-semantics && bundle exec ruby -e "..."
```
Commit `Gemfile` and `Gemfile.lock` (probes are applications, not libraries — lock the versions); gitignore `vendor/bundle/` and `.bundle/`.

The probe file's Command section records the `cd` so it remains copy-pasteable.

### Tier 3 — not a probe anymore

When a "probe" needs a real project layout — multiple source files, fixtures, a test runner, an external service running locally — it has outgrown `probes/`. Move it to `~/Code/Learning/<topic>/` (or wherever scratch projects live) and link back from the relevant wiki page. Probes are kernel-cell-sized; full scratch projects are not.

### Rule of thumb

If the probe's Command section takes more than ~4 lines once deps are included, either drop to Tier 2 or accept it has become a mini-project (Tier 3). A 20-line inline shell heredoc is a smell.

## When to skip probes

- Theory-only concepts where no small snippet demonstrates the point (ethics, threat modeling, architectural tradeoffs without a runnable comparison).
- Topics where the probe would require shared-system access the dev doesn't have.
- When the dev has already internalized the fact and the probe would be ceremony.

## Template

`probes/_template.md` is a blank probe file. Copy it when scaffolding a new one. The leading underscore keeps it out of any topic-slug directory listings.

## Linking probes to wiki pages

The link is **one-way and derived.** Each probe's frontmatter has a `wiki:` field pointing up to its wiki page. Wiki pages do **not** store a list of their probes — that would dual-maintain and drift.

To list probes for a wiki page, run:

```bash
scripts/wiki-probes architecture/event-sourcing
scripts/wiki-probes --count architecture/event-sourcing
scripts/wiki-probes --topic event-sourcing    # alternative: match by topic folder
scripts/wiki-probes                            # all probes grouped by wiki page
```

`/study` Phase 2 wiki review calls this automatically and surfaces probes as optional recall checks. A probe whose output the developer can no longer predict is a real recall gap, not a trivial re-read.

## Cross-references

- Spec: `.claude/skills/study-walkthrough/SKILL.md` → Phase 2 "Probe when possible" bullet
- Wiki review hook: `.claude/skills/study/SKILL.md` → Phase 2 Step 2a
- Lookup script: `scripts/wiki-probes`
- Principles: `AGENTS.md` → Skill Design Principles
- Methodology source: the Solveit page in the master-terminal wiki (`wiki/solveit-method.md`)
