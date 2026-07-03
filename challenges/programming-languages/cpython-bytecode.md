---
wiki: programming-languages/compilers-and-interpreters
section: "Case study: the CPython chain"
kind: predict-output
env: python312
questions:
- Why does compile() not execute the code?
- What consumes these opcodes, the CPU or something else?
created: 2026-07-03
---

## Brief

Does this print hi, or something else? Predict the exact output before running.

## Stub

```python
import dis

dis.dis(compile('print("hi")', "<src>", "exec"))
```

## Solution

```python
import dis

dis.dis(compile('print("hi")', "<src>", "exec"))
```

## Expected Output

```
  0           0 RESUME                   0

  1           2 PUSH_NULL
              4 LOAD_NAME                0 (print)
              6 LOAD_CONST               0 ('hi')
              8 CALL                     1
             16 POP_TOP
             18 RETURN_CONST             1 (None)
```
