---
wiki: software-design/reading-code-for-intent
section: Tradeoffs and gotchas
kind: predict-output
env: python312
questions:
- Why can a contract that catches misuse in development silently permit it in production?
- Which rung of the ladder survives stripping, and why?
created: 2026-07-04
---

## Brief

The same one-line program runs under a normal interpreter and under python -O, which strips assert statements. Predict what each run prints.

## Stub

```python
import subprocess, sys

code = "assert False, 'precondition violated'; print('shipped anyway')"

debug = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
release = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)

print("debug:  ", (debug.stdout or debug.stderr).strip().splitlines()[-1])
print("release:", (release.stdout or release.stderr).strip().splitlines()[-1])
```

## Solution

```python
import subprocess, sys

code = "assert False, 'precondition violated'; print('shipped anyway')"

debug = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
release = subprocess.run([sys.executable, "-O", "-c", code], capture_output=True, text=True)

print("debug:  ", (debug.stdout or debug.stderr).strip().splitlines()[-1])
print("release:", (release.stdout or release.stderr).strip().splitlines()[-1])
```

## Expected Output

```
debug:   AssertionError: precondition violated
release: shipped anyway
```
