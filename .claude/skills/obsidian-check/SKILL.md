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

Check if Obsidian is already running by testing for its CLI socket. Only launch if it's not connected:
```bash
test -S "${XDG_RUNTIME_DIR:-$HOME}/.obsidian-cli.sock" || (snap run obsidian &>/dev/null & disown && sleep 3)
```

If the socket exists, Obsidian is running and the CLI can connect — skip launch. Do not use `pgrep -f "obsidian"`: it self-matches the shell eval context and gives false positives.

### Step 2: Run Health Checks

```bash
# Standalone lint (always works)
scripts/lint wiki

# Obsidian CLI checks (only if connected)
obsidian unresolved vault="study"
obsidian orphans vault="study"
obsidian deadends vault="study"
obsidian tags counts vault="study"
```

### Step 3: Report

Present a clean summary:

> **Wiki Health Check**
>
> Pages: 12 | Tags: 8 | Links: 34
>
> **Lint (standalone):** Clean
>
> **Obsidian CLI:**
> - Unresolved links: 2 (`[[architecture/saga-pattern]]`, `[[security/oauth]]`)
> - Orphan pages: 1 (`javascript/old-notes.md`)
> - Dead-end pages: 0
>
> **Suggestions:**
> - Create pages for unresolved links, or remove the links
> - Add outgoing links to orphan pages, or delete them

### Step 4: Open Pages (if requested)

If the developer asked to open a specific page:
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
- Always run the standalone lint even if Obsidian CLI fails — it's the reliable fallback
