---
name: obsidian-check
description: "Launch Obsidian, run wiki health checks via CLI (unresolved links, orphans, dead-ends), and open specific pages. Trigger keywords: obsidian check, wiki health, check links, open obsidian."
user_invocable: true
---

# /obsidian-check — Wiki Health Check via Obsidian CLI

Launch Obsidian, run the full CLI lint suite, and report wiki health. Can also open specific pages in the Obsidian GUI.

## Invocation

```
/obsidian-check                    — Full health check
/obsidian-check <page>             — Open a specific page in Obsidian
/obsidian-check --lint-only        — Run lint script without Obsidian
```

## Flow

### Step 1: Launch Obsidian GUI

Check if the official CLI is connected by testing for its socket. Only launch if it's not:
```bash
test -S "${XDG_RUNTIME_DIR:-$HOME}/.obsidian-cli.sock" || { setsid -f /opt/Obsidian/obsidian >/dev/null 2>&1 < /dev/null; sleep 3; }
```

The socket (`/run/user/1000/.obsidian-cli.sock`) means Obsidian is running and the CLI is connected — skip launch. Obsidian is the Debian package at `/opt/Obsidian/obsidian` (no `snap` on this machine). Do not use `pgrep -f "obsidian"`: the `-f` form matches the full command line and self-matches the shell eval context.

### Step 2: Run Health Checks

```bash
# Standalone lint — authoritative (respects allow_orphan, frontmatter, slug drift)
scripts/lint wiki

# Obsidian CLI checks (graph-level; only if socket connected)
obsidian unresolved vault="study"
obsidian orphans vault="study"
obsidian deadends vault="study"
```

`scripts/lint` is authoritative for orphans because it honors `allow_orphan: true` (the `*-index.md` MOCs are intentional orphans); the `obsidian orphans` CLI does not know about that flag and will also list `indexes/index.db`, so treat its orphan output as raw graph data, not violations.

### Step 3: Report

Present a clean summary:

> **Wiki Health Check**
>
> Pages: 12 | Tags: 8 | Links: 34
>
> **Lint:**
> - Unresolved links: 2 (`[[architecture/saga-pattern]]`, `[[security/oauth]]`)
> - Orphan pages: 1 (`javascript/old-notes.md`)
> - Alias collisions: 0
>
> **Suggestions:**
> - Create pages for unresolved links, or remove the links
> - Add outgoing links to orphan pages, or delete them

### Step 4: Open Pages (if requested)

If the developer asked to open a specific page (`<slug>` = wiki-relative path without `.md`):
```bash
obsidian open vault="study" file="<slug>"
```

## Standalone Mode (--lint-only)

When invoked with `--lint-only`, skip Obsidian entirely:
```bash
scripts/lint wiki
```

## Guardrails

- Never force-close or restart Obsidian
- `scripts/lint wiki` is the authoritative health check; the GUI is only for visual inspection and opening pages
