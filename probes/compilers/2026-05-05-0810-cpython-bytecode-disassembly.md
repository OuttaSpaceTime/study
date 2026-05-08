---
topic: compilers
session: 2026-05-05-walkthrough
wiki: programming-languages/compilers-and-interpreters
created: 2026-05-05 08:10
---

## Prediction

`python3 -c "import dis; dis.dis(compile('print(\"hi\")', '<src>', 'exec'))"` will print `hi`.

## Command

```bash
python3 -c "import dis; dis.dis(compile('print(\"hi\")', '<src>', 'exec'))"
```

## Output

```
  0           0 RESUME                   0

  1           2 PUSH_NULL
              4 LOAD_NAME                0 (print)
              6 LOAD_CONST               0 ('hi')
              8 CALL                     1
             16 POP_TOP
             18 RETURN_CONST             1 (None)
```

## Takeaway

Wrong prediction. `compile()` does not run the code — it produces a bytecode object, and `dis.dis()` prints that object's instructions. The opcodes (`LOAD_NAME`, `CALL`, `RETURN_CONST`) are inputs to the CPython virtual machine, not CPU instructions. The CPU is running CPython itself (a C program compiled to machine code); the user's `.py` file becomes *data* that CPython reads one opcode at a time. The compiler card has been lapsing because the mental model assumed `.py` → machine code directly; the real chain is `.py` → tokens → AST → bytecode → consumed by the VM, which is the only thing the CPU sees.
