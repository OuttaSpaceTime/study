---
wiki: git/git-restore
section: "--source: Restoring from Any Commit"
kind: write-code
env: python312
questions:
- Why are both --staged and --worktree needed here to leave the file staged and ready to commit?
- What would git restore --source=HEAD~2 f.txt without any target flags have changed?
created: 2026-07-03
---

## Brief

f.txt went through three commits with contents v1, v2, v3. Write the one restore command that rewinds it to the content from two commits ago, staged and ready to commit, without moving the branch.

## Stub

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q && git config user.email t@t && git config user.name t")
for i, v in enumerate(["v1", "v2", "v3"], 1):
    Path("f.txt").write_text(v + "\n")
    sh(f"git add f.txt && git commit -qm c{i}")
# TODO: one git restore command that sets f.txt back to its content two
# commits ago, in BOTH the index and the worktree
sh("git restore TODO")
print("index:", sh("git show :f.txt"))
print("worktree:", Path("f.txt").read_text().strip())
print("status:", sh("git status --porcelain"))
```

## Solution

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q && git config user.email t@t && git config user.name t")
for i, v in enumerate(["v1", "v2", "v3"], 1):
    Path("f.txt").write_text(v + "\n")
    sh(f"git add f.txt && git commit -qm c{i}")
sh("git restore --source=HEAD~2 --staged --worktree f.txt")
print("index:", sh("git show :f.txt"))
print("worktree:", Path("f.txt").read_text().strip())
print("status:", sh("git status --porcelain"))
```

## Expected Output

```
index: v1
worktree: v1
status: M  f.txt
```
