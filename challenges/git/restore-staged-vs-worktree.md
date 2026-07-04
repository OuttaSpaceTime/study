---
wiki: git/git-restore
section: "Targets: --worktree and --staged"
kind: predict-output
env: python312
questions:
- Which of the three states HEAD, index, and worktree does git restore --staged overwrite, and from where does the content come?
- After this snippet runs, what single command would also discard the v3 edit in the worktree?
created: 2026-07-03
---

## Brief

f.txt holds three different contents at once. HEAD has v1, the index has v2, and the worktree has v3. Predict what `git restore --staged` changes along the HEAD to index to worktree pipeline.

## Stub

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q && git config user.email t@t && git config user.name t")
Path("f.txt").write_text("v1\n")
sh("git add f.txt && git commit -qm c1")
Path("f.txt").write_text("v2\n")
sh("git add f.txt")
Path("f.txt").write_text("v3\n")
print("index before:", sh("git show :f.txt"))
sh("git restore --staged f.txt")
print("index after:", sh("git show :f.txt"))
print("worktree:", Path("f.txt").read_text().strip())
```

## Solution

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q && git config user.email t@t && git config user.name t")
Path("f.txt").write_text("v1\n")
sh("git add f.txt && git commit -qm c1")
Path("f.txt").write_text("v2\n")
sh("git add f.txt")
Path("f.txt").write_text("v3\n")
print("index before:", sh("git show :f.txt"))
sh("git restore --staged f.txt")
print("index after:", sh("git show :f.txt"))
print("worktree:", Path("f.txt").read_text().strip())
```

## Expected Output

```
index before: v2
index after: v1
worktree: v3
```
