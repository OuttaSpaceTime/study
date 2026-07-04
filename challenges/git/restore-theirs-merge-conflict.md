---
wiki: git/git-restore
section: "--ours and --theirs During Merge Conflicts"
kind: predict-output
env: python312
questions:
- During a merge on main, which branch does --theirs refer to, and why is the file still listed as UU afterward?
- How do --ours and --theirs flip during a rebase, and why?
created: 2026-07-03
---

## Brief

main and feature both edited f.txt, so merging feature into main conflicts. Predict which content `git restore --theirs` picks and what the status shows afterward.

## Stub

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q -b main && git config user.email t@t && git config user.name t")
Path("f.txt").write_text("base\n")
sh("git add f.txt && git commit -qm base")
sh("git switch -qc feature")
Path("f.txt").write_text("from feature\n")
sh("git commit -qam feature-change")
sh("git switch -q main")
Path("f.txt").write_text("from main\n")
sh("git commit -qam main-change")
sh("git merge feature")
sh("git restore --theirs -- f.txt")
print("content:", Path("f.txt").read_text().strip())
print("status:", sh("git status --porcelain"))
```

## Solution

```python
import subprocess, tempfile, os
from pathlib import Path
os.chdir(tempfile.mkdtemp())
sh = lambda c: subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
sh("git init -q -b main && git config user.email t@t && git config user.name t")
Path("f.txt").write_text("base\n")
sh("git add f.txt && git commit -qm base")
sh("git switch -qc feature")
Path("f.txt").write_text("from feature\n")
sh("git commit -qam feature-change")
sh("git switch -q main")
Path("f.txt").write_text("from main\n")
sh("git commit -qam main-change")
sh("git merge feature")
sh("git restore --theirs -- f.txt")
print("content:", Path("f.txt").read_text().strip())
print("status:", sh("git status --porcelain"))
```

## Expected Output

```
content: from feature
status: UU f.txt
```
