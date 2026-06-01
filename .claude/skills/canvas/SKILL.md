---
name: canvas
description: "Interactively edit an Obsidian canvas in a tight edit→show→react loop. Two modes — live (eval, reads your GUI selection, instant) and file (JSON on disk, git-trackable). Trigger keywords: canvas, edit canvas, obsidian canvas, canvas node, mind map, diagram canvas."
user_invocable: true
---

# /canvas — Interactive Obsidian Canvas Editing

Drive an Obsidian `.canvas` file in a back-and-forth loop: you point (by selecting nodes in the GUI or by describing them), I make **one** change, persist it, and show you the result via screenshot. Then you react. Repeat.

A `.canvas` file is plain JSON — `{ "nodes": [...], "edges": [...] }` — so both editing modes write the **same schema**. The only difference is the channel.

## Invocation

```
/canvas <name>            — open/create <name>.canvas and start the loop (mode auto-picked)
/canvas <name> --live     — force live mode (eval against the running app)
/canvas <name> --file     — force file mode (Read/Write the JSON on disk)
/canvas                    — operate on the currently-open canvas (live mode)
```

`<name>` is a vault-relative slug without extension (e.g. `diagrams/auth-flow`). Create under a sensible folder; bare names land at vault root.

## The two modes

| | **File mode** (JSON) | **Live mode** (`eval`) |
|---|---|---|
| Channel | `Read`/`Write` the `.canvas` file | `obsidian eval code='…'` against the running app |
| Shows in the open GUI | **Yes** — Obsidian file-watches the canvas and auto-reloads on disk change (tab must already be open) | Yes — reflects in the open GUI |
| Reads your GUI selection | No — you reference nodes by id/text | **Yes** — `getSelectionData()` is the shared pointer (the discriminator) |
| Git diffability | **Native** — clean, reviewable diffs | Same artifact on disk, but edits aren't authored as a diff |
| Robustness | Stable, inspectable, no shell-escaping | Internal API, undocumented, may shift across Obsidian versions; shell-escaping pain for big edits |
| Best for | The default — structural/bulk edits, edges, durable diffs, any committed artifact | Acting on the developer's current selection ("expand *this*") and other live-state-only beats |

**Default: file mode (direct JSON `Read`/`Write`).** It refreshes in the GUI just as live as `eval` does — Obsidian watches the file and auto-reloads the open canvas on disk change — while producing clean git-trackable diffs and avoiding shell-escaping. Since a canvas is usually a committed artifact, direct editing is the better fit. Reserve **live `eval` mode for things direct editing cannot do** — primarily acting on the developer's current GUI selection without them naming the node, or reading other live in-memory state. The persisted artifact on disk is identical either way; you can switch modes mid-session. State which mode you're in at the start of the loop.

## Flow

### Step 1 — Preflight (silent)

Ensure Obsidian + CLI are up (only launch if the socket is absent):
```bash
test -S "${XDG_RUNTIME_DIR:-$HOME}/.obsidian-cli.sock" || { setsid -f /opt/Obsidian/obsidian >/dev/null 2>&1 < /dev/null; sleep 3; }
```
Resolve the target. If `<name>.canvas` doesn't exist, create a minimal one and open it; otherwise just open it. `obsidian open` is only for the **initial open** (or to bring the tab forward if it isn't focused) — once the canvas tab is open, subsequent file-mode edits auto-refresh via file-watch without reopening:
```bash
obsidian open vault="study" file="<name>.canvas"
```
Before any *live* edit (only needed in live mode), confirm the canvas view is active:
```bash
obsidian eval code='app.workspace.getLeavesOfType("canvas")[0] ? "ready" : "no canvas leaf"'
```

### Step 2 — Read current state (silent)

- **Live:** read the full graph and the developer's selection — the selection is what "this" refers to.
  ```bash
  obsidian eval code='JSON.stringify(app.workspace.getLeavesOfType("canvas")[0].view.canvas.getSelectionData())'
  ```
- **File:** `Read` the `.canvas` file.

Per the repo's read-silently rule, **never paste the JSON or eval output into chat.** Synthesize: "3 nodes, you've got the 'Auth' node selected."

### Step 3 — One change per beat

Make the single change the developer asked for. Prefer the right tool:

- **File mode (the default path):** `Read` → edit the JSON → `Write`. Obsidian file-watches the canvas and auto-reloads it in the open tab on disk change — no `obsidian open` needed for the refresh; only call it if the tab isn't open yet or needs bringing forward. This is the primary path for structural/bulk edits, edges, and any committed artifact, and it produces clean git diffs.
- **Live `eval` fallback — selection-driven beats only.** Reach for these recipes when the change must act on the developer's current GUI selection (or other live in-memory state) that file mode can't see:
  - **Single text node:**
    ```bash
    obsidian eval code='app.workspace.getLeavesOfType("canvas")[0].view.canvas.createTextNode({pos:{x:0,y:120},size:{width:260,height:80},text:"…",save:true})'
    ```
  - **Anything structural (edges, multiple nodes, moves):** read → mutate the plain object → write back. This avoids the low-level `addEdge` constructor and all shell-escaping of nested edits:
    ```bash
    obsidian eval code='(()=>{const c=app.workspace.getLeavesOfType("canvas")[0].view.canvas; const d=c.getData(); d.edges.push({id:"e-new",fromNode:"n1",fromSide:"bottom",toNode:"n2",toSide:"top"}); c.setData(d); c.requestSave(); return "edge added"})()'
    ```
    (For larger mutations, write the JS to compute the new `d` rather than hand-escaping a long inline string — or just use file mode.)

### Step 4 — Persist + show (the feedback half)

Live edits with `save:true` (or `requestSave()`) already hit disk. Then **show the result** — this is the anti-slot-machine half of the loop, never skip it:
```bash
obsidian eval code='(()=>{const l=app.workspace.getLeavesOfType("canvas")[0]; app.workspace.setActiveLeaf(l,{focus:true}); l.view.canvas.zoomToFit(); return "focused"})()'
obsidian dev:screenshot path="/tmp/canvas_shot.png"
```
Then `Read /tmp/canvas_shot.png` and describe in one line what changed. Use `zoomToSelection()` instead of `zoomToFit()` when iterating on one region.

### Step 5 — React loop

Ask what's next. The developer may now select different nodes in the GUI; on the next beat, re-read `getSelectionData()` so "this one" resolves correctly. Keep changes atomic — one edit, one screenshot, one decision. Correct in place: if a previous edit was wrong, fix that node, don't append a contradicting one.

### Step 6 — Session log

On exit, append a `## Session N — Change (HH:MM)` entry to today's `logs/<MM>/<YYYY-MM-DD>.md` — **Files:** the `.canvas` path, **Change:** what was built, **Why:** the developer's stated intent.

## Canvas JSON schema (verified)

**Node** — `id` (string), `type` (`text` | `file` | `link` | `group`), `x`, `y`, `width`, `height`, optional `color`. Type-specific payload:
- `text` → `text` (markdown string)
- `file` → `file` (vault-relative path), optional `subpath` (`#heading` or `#^block`)
- `link` → `url`
- `group` → `label`

**Edge** — `id`, `fromNode`, `fromSide` (`top`|`right`|`bottom`|`left`), `toNode`, `toSide`, optional `label`, `color`, `fromEnd`/`toEnd` (`none`|`arrow`).

## Live API cheat-sheet (verified on this machine)

Handle: `const c = app.workspace.getLeavesOfType("canvas")[0].view.canvas`

- **Bulk (preferred for structure):** `c.getData()` → mutate → `c.setData(d)` → `c.requestSave()`. Same shape as the file.
- **Create:** `c.createTextNode({pos,size,text,save})`, `c.createFileNode({pos,size,file,subpath,save})`, `c.createLinkNode({pos,size,url,save})`, `c.createGroupNode({pos,size,label,save})`
- **Remove:** `c.removeNode(node)`, `c.deleteSelection()`
- **Select / read:** `c.getSelectionData()`, `c.selectOnly(node)`, `c.deselectAll()`, `c.getViewportNodes()`
- **View:** `c.zoomToFit()`, `c.zoomToSelection()`, `c.zoomToBbox(bbox)`, `c.nudgeSelection(dx,dy)`
- **Persist:** `c.requestSave()`

`eval` evaluates an **expression** and returns it — no top-level `return`. Wrap multi-statement logic in an IIFE `(()=>{ … ; return x })()`. `dev:screenshot path=…` captures the whole window; focus the canvas leaf first.

## Guardrails

- **Read silently.** Never dump canvas JSON, `getData()` output, or eval results into chat — speak only the synthesized state, the change made, and the next question.
- **One change per beat**, always followed by a screenshot. No fire-and-forget batches (anti-slot-machine).
- **Human is the agent.** On ambiguity ("which node?") ask, or read the live selection — don't guess and auto-edit.
- **Selection is the pointer** in live mode; re-read it each beat rather than assuming it's unchanged.
- Prefer **file mode** when an edit is large enough that inline JS escaping gets fragile, or when the developer wants a reviewable diff.
- Never force-close or restart Obsidian. Don't launch it unconditionally — check the socket first.
- The live API is internal/undocumented; if a method is missing on this Obsidian version, fall back to file mode rather than guessing alternatives.
