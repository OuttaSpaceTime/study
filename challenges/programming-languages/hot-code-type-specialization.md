---
wiki: programming-languages/compilers-and-interpreters
section: "JIT: when bytecode becomes machine code at runtime"
kind: predict-output
env: python312
questions:
- Which runtime observation lets the interpreter swap in the specialized instruction?
- What would happen to this specialization if add were now called with two strings?
created: 2026-07-03
---

## Brief

A JIT specializes hot code for the types it observes at runtime. CPython 3.12 does the observe-and-specialize half in pure bytecode. Predict what the BINARY_OP line looks like after the loop makes add hot with ints.

## Stub

```python
import dis

def add(x, y):
    return x + y

for _ in range(64):
    add(1, 2)

dis.dis(add, adaptive=True)
```

## Solution

```python
import dis

def add(x, y):
    return x + y

for _ in range(64):
    add(1, 2)

dis.dis(add, adaptive=True)
```

## Expected Output

```
  3           0 RESUME                   0

  4           2 LOAD_FAST__LOAD_FAST     0 (x)
              4 LOAD_FAST                1 (y)
              6 BINARY_OP_ADD_INT        0 (+)
             10 RETURN_VALUE
```
