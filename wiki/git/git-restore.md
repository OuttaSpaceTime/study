---
title: git restore
aliases:
- git restore command
- restore files git
tags:
- git
- version-control
created: '2026-04-09'
updated: '2026-04-22'
source_skill: study-walkthrough
flashcard_ids:
- cmne7xz9202lx0msonsbfhp3j
- cmne7xz1y02k30msouw64srcz
- cmne7xyv602if0msoa0ryw0o7
- cmne7xyw902in0msoac5c4qm5
- cmne7xyox02gx0msovt0cjf5p
- cmne7xyge02ez0msohehvs3gj
- cmne7xyd402e70mso1xuwru3o
- cmne7xya902dh0msotg5sajyw
- cmne7xy9k02d90mso2ibigeht
depth: 1
last_deepened: '2026-04-09'
next_review: '2026-05-27'
review_interval: 25
probe_sections:
- 'Targets: --worktree and --staged'
- '--source: Restoring from Any Commit'
- --ours and --theirs During Merge Conflicts
- '--merge: Recreate Conflict State'
- Conflicts from `git stash pop`
- --ignore-unmerged
- 'Interactive: -p'
- Common Patterns
last_probed:
- 'Interactive: -p'
- Common Patterns
- 'Targets: --worktree and --staged'
- '--source: Restoring from Any Commit'
- --ours and --theirs During Merge Conflicts
- Conflicts from `git stash pop`
- '--merge: Recreate Conflict State'
- --ignore-unmerged
---

# git restore

`git restore` restores file contents from a source. It replaces the older `git checkout -- <file>` and `git reset HEAD <file>` workflows with explicit, composable flags.

## Targets: --worktree and --staged

`git restore` takes one or more **targets** — what to overwrite:

- `--worktree` (default): overwrites the file on disk from the index
- `--staged`: overwrites the index from HEAD
- `--staged --worktree`: overwrites both from HEAD (or an explicit `--source`)

```bash
git restore file.txt                  # worktree ← index
git restore --staged file.txt         # index ← HEAD
git restore --staged --worktree file.txt  # both ← HEAD
```

The pipeline is: `HEAD → index → worktree`. Each flag copies one step leftward.

## --source: Restoring from Any Commit

Override the default source with `--source`:

```bash
git restore --source=HEAD~3 -- src/auth.ts   # worktree ← 3 commits ago
git restore --source=v2.0 -- src/api.ts      # worktree ← tag v2.0
git restore --source=HEAD~3 --staged --worktree -- file.txt  # both ← old commit
```

This is the cleanest way to rewind a single file without checking out a branch.

## --ours and --theirs During Merge Conflicts

During an active merge conflict, `--ours`/`--theirs` refer to the two sides:

- `--ours`: keep the **current branch** (destination)
- `--theirs`: keep the **incoming branch** (source)

```bash
git restore --ours -- utils.ts    # keep current branch version
git restore --theirs -- utils.ts  # keep incoming branch version
git add utils.ts                  # mark as resolved
```

**In a rebase**, the sides flip — because git replays your commits onto the new base:
- `--ours`: the branch being rebased **onto** (new base)
- `--theirs`: the commits being replayed (your original branch)

**After resolution** (no active conflict): `--ours` falls back to HEAD. `--theirs` restores the unresolved incoming version from the index.

## --merge: Recreate Conflict State

```bash
git restore --merge -- config.ts
```

Recreates conflict markers in a resolved file. Useful when you want to re-approach a resolution.

## Conflicts from `git stash pop`

`git stash pop` applies the stash as a 3-way merge: HEAD is **ours**, the stash is **theirs**. Semantics match a normal merge — **not** inverted like rebase.

```bash
git stash pop                         # conflict in utils.ts
git restore --ours -- utils.ts        # discard the stashed change, keep HEAD
git restore --theirs -- utils.ts      # keep the stashed change, discard HEAD
git add utils.ts
git stash drop                        # pop leaves the stash on failure — drop manually
```

The `git stash drop` is the stash-specific trap: a successful pop auto-drops, but a **conflicted** pop does not. Without it, the stash stays on the stack and you'll re-apply the same conflict next time.

## --ignore-unmerged

```bash
git restore --ignore-unmerged
```

Skips unmerged paths during a restore — other files are restored normally.

## Interactive: -p

```bash
git restore -p          # interactively select hunks to discard
git restore -p file.txt # same, scoped to one file
```

## Common Patterns

```bash
# Unstage a file
git restore --staged debug.log

# Discard unstaged changes
git restore debug.log

# Unstage AND wipe worktree in one command
git restore --staged --worktree -- debug.log

# Recover a deleted file from a tag
git restore --source=v1.0 deleted-file.txt

# Reset a file to 3 commits ago, staged and ready to commit
git restore --source=HEAD~3 --staged --worktree -- src/auth.ts
```
