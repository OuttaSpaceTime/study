---
wiki: git/git-restore
section: "Conflicts from `git stash pop`"
kind: predict-output
env: python312
questions:
- Why does the stash still appear in git stash list after this pop?
- In a stash pop conflict, which side is theirs, and what two commands finish the cleanup after resolving?
created: 2026-07-03
---

## Brief

A stashed edit and a later commit both changed f.txt, so `git stash pop` conflicts. Predict how many stashes remain on the stack and which content `git restore --theirs` picks.

## Stub

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q && git config user.email t@t && git config user.name t")
Path("f.txt").write_text("v1\n")
sh("git add f.txt && git commit -qm c1")
Path("f.txt").write_text("stashed edit\n")
sh("git stash -q")
Path("f.txt").write_text("committed edit\n")
sh("git commit -qam c2")
sh("git stash pop")
print("stashes left:", sh("git stash list | wc -l"))
sh("git restore --theirs -- f.txt")
print("content:", Path("f.txt").read_text().strip())
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
Path("f.txt").write_text("stashed edit\n")
sh("git stash -q")
Path("f.txt").write_text("committed edit\n")
sh("git commit -qam c2")
sh("git stash pop")
print("stashes left:", sh("git stash list | wc -l"))
sh("git restore --theirs -- f.txt")
print("content:", Path("f.txt").read_text().strip())
```

## Expected Output

```
stashes left: 1
content: stashed edit
```
