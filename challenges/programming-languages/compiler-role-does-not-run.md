---
wiki: programming-languages/compilers-and-interpreters
section: "Compiler vs interpreter: roles, not languages"
kind: predict-output
env: python312
questions:
- Which line plays the compiler role and which plays the interpreter role?
- What kind of artifact sits between the two lines, and can the CPU execute it directly?
created: 2026-07-03
---

## Brief

CPython exposes both roles as builtins. Predict exactly what prints and in which order.

## Stub

```python
artifact = compile('print("running now")', "<src>", "exec")
print("compile returned:", type(artifact).__name__)
exec(artifact)
```

## Solution

```python
artifact = compile('print("running now")', "<src>", "exec")
print("compile returned:", type(artifact).__name__)
exec(artifact)
```

## Expected Output

```
compile returned: code
running now
```
