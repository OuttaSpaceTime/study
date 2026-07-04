---
wiki: programming-languages/compilers-and-interpreters
section: "Two orthogonal axes: type checking ⊥ compile target"
kind: predict-output
env: python312
questions:
- At which stage does CPython verify types, and at which stage would rustc have rejected this?
- Why does a compiler that skips type checking prove the two axes are independent?
created: 2026-07-03
---

## Brief

This snippet feeds an obvious type error to CPython's compiler. Predict whether the failure happens at compile time or at run time, and what prints.

## Stub

```python
code = compile('x = "a" + 1', "<src>", "exec")
print("compiled without complaint")
try:
    exec(code)
except TypeError as e:
    print("at runtime:", e)
```

## Solution

```python
code = compile('x = "a" + 1', "<src>", "exec")
print("compiled without complaint")
try:
    exec(code)
except TypeError as e:
    print("at runtime:", e)
```

## Expected Output

```
compiled without complaint
at runtime: can only concatenate str (not "int") to str
```
