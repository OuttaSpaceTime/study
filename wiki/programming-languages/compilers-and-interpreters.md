---
title: Compilers and Interpreters
aliases:
- compiler
- interpreter
- bytecode
- JIT
- virtual machine
- Python execution model
tags:
- compilers
- programming-languages
- interpreters
- bytecode
- jit
created: '2026-05-05'
updated: '2026-05-05'
source_skill: study-walkthrough
last_deepened: '2026-05-05'
review_interval: 2
next_review: '2026-07-02'
probe_sections:
- 'Compiler vs interpreter: roles, not languages'
- 'Two orthogonal axes: type checking ⊥ compile target'
- 'Case study: the CPython chain'
- 'JIT: when bytecode becomes machine code at runtime'
last_probed:
- 'Compiler vs interpreter: roles, not languages'
- 'Case study: the CPython chain'
- 'JIT: when bytecode becomes machine code at runtime'
- 'Two orthogonal axes: type checking ⊥ compile target'
allow_orphan: true
flashcard_ids: []
---

# Compilers and Interpreters

## TL;DR

- A **compiler** is a *translator* between languages (source A → target B). An **interpreter** is an *executor* (reads a program and produces its effects). They are roles, not language properties. Most modern toolchains use both.
- Whether a language is **statically vs dynamically typed** is independent of whether it **compiles to machine code, bytecode, or stays as source**. Two orthogonal axes: Java is static + bytecode, Python is dynamic + bytecode, Rust is static + machine code, V8 JITs dynamic JS to machine code.
- "Python is slow because it's dynamically typed" is the wrong framing. CPython is slow because it **interprets bytecode**. PyPy proves the gap is closeable by JIT-compiling that same bytecode to machine code.

## Compiler vs interpreter: roles, not languages

The lapse-driving mental model treats "compiler" as something tied to a specific language ("C is compiled, Python is interpreted"). The crisper definition is role-based.

- **Compiler**: input is a program in language A. Output is an equivalent program in language B. **It does not run the program.** Examples: `gcc` (C → machine code), `tsc` (TypeScript → JavaScript), `rustc` (Rust → machine code), the compiler inside CPython (Python → bytecode), `javac` (Java → JVM bytecode).
- **Interpreter**: input is a program in some language. Output is the actual effects of running it (printing, mutating state, returning values). **It does not produce a translated artifact.** Examples: a pure tree-walking interpreter for a toy language, the CPython VM (interprets bytecode), the JVM's interpreter mode.

A toolchain can use either, both, or chain them:

- **C / Rust / Go**: compiler only. Source compiles directly to machine code; the OS loader hands the binary to the CPU.
- **Pure interpreter**: interpreter only. Reads source and executes; no compiled artifact.
- **CPython / Java / C# / Ruby (YARV)**: both, chained. A compiler produces bytecode; an interpreter (the VM) consumes that bytecode.

The "compiler" card kept lapsing because the back said *"converts a programming language into instructions a computer can understand and run."* That phrasing assumes the target is always machine code. It isn't. `tsc`'s output (JavaScript) is not "instructions a computer can understand"; it still needs a runtime.

## Two orthogonal axes: type checking ⊥ compile target

Two unrelated language design decisions get conflated all the time:

| Axis                     | What it answers                               | Choices                                                                              |
| ------------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------ |
| **Type checking time**   | When are types verified?                      | Static (at compile time) · Dynamic (at runtime)                                      |
| **Translation strategy** | How is source turned into something runnable? | AOT to machine code · AOT to bytecode (then interpreted) · Pure interpretation · JIT |

These mix freely:

| Language | Type checking | Compile target |
|---|---|---|
| Rust | static | machine code (AOT) |
| Go | static | machine code (AOT) |
| Java | static | bytecode (.class) |
| C# | static | bytecode (CIL) |
| Python (CPython) | dynamic | bytecode |
| Ruby (YARV) | dynamic | bytecode |
| Python (PyPy) | dynamic | bytecode → JIT to machine code |
| JavaScript (V8) | dynamic | bytecode → JIT to machine code |

**Counter-examples that prove independence:**

- **Java is statically typed and compiles to bytecode.** If "static = compile to machine code" held, Java's toolchain couldn't exist.
- **PyPy runs the same dynamically-typed Python as CPython, ~5–10× faster.** If "dynamic = slow" were the dominant story, PyPy couldn't close the gap.

Static typing *enables* certain optimizations and AOT machine-code compilation. It does not *require* either.

## Case study: the CPython chain

What actually happens when you run `python3 hello.py`:

```
hello.py
   ↓ lexer
tokens         flat list: print ( "hi" )
   ↓ parser
AST            tree: Module → Expr → Call(func=Name(print), args=[Constant("hi")])
   ↓ compiler  (walks the tree, emits opcodes)
bytecode       LOAD_NAME, CALL, RETURN_CONST...
   ↓ CPython VM (interpreter loop, written in C, compiled to machine code)
CPU            runs the VM, which is reading bytecode opcodes one at a time
```

The CPU is **never running the user's `.py` code as machine code.** What the CPU executes is **CPython itself**. A C program that's been compiled to machine code. The user's program lives as bytecode, *data* fed to that VM.

### Probe 1: bytecode is real

```bash
python3 -c "import dis; dis.dis(compile('print(\"hi\")', '<src>', 'exec'))"
```

Output (CPython 3.12):

```
  0           0 RESUME                   0

  1           2 PUSH_NULL
              4 LOAD_NAME                0 (print)
              6 LOAD_CONST               0 ('hi')
              8 CALL                     1
             16 POP_TOP
             18 RETURN_CONST             1 (None)
```

Each line is one stack-machine instruction for the CPython VM. Not CPU instructions. The CPU has no idea what `LOAD_NAME` means.

### Probe 2: the AST always wraps in Module

```bash
python3 -c "import ast; print(ast.dump(ast.parse('print(\"hi\")'), indent=2))"
```

Output:

```
Module(
  body=[
    Expr(
      value=Call(
        func=Name(id='print', ctx=Load()),
        args=[Constant(value='hi')],
        keywords=[]))],
  type_ignores=[])
```

Even a single-line program is wrapped in `Module(body=[...])`. The parser thinks "a file is a list of statements". That uniform shape is what lets the compiler iterate `Module.body` and emit bytecode for each entry.

## JIT: when bytecode becomes machine code at runtime

PyPy, V8, .NET, LuaJIT, GraalVM. All start with the same compile-to-bytecode setup as CPython, but add a runtime stage CPython lacks:

1. The VM starts by interpreting bytecode (fast warm-up, no compile cost).
2. As the program runs, the VM tracks **which functions get hot** (called many times, looped over).
3. Hot bytecode is compiled to **native machine code**, often **specialized for the runtime types observed** (e.g., V8 sees `add(x, y)` always called with `Number, Number`. Emits an integer-add machine instruction; if a string ever shows up, it deoptimizes back to the generic path).
4. The CPU runs the JIT-emitted machine code directly for hot paths; cold code stays interpreted.

This is why **dynamic typing is not the dominant cost** of Python's slowness:

- CPython's bottleneck is *interpretation overhead*: fetching opcodes, dispatching through a switch, dict lookups for every name access.
- PyPy interprets the same bytecode but JITs hot loops to specialized machine code, gaining 5–10× while keeping full Python dynamic-typing semantics.
- The difference between CPython and PyPy is the **runtime strategy**, not the **language**.

V8 makes the same point for JavaScript. Same dynamic-typed source, near-native speed for hot code.

## Related Concepts

(None yet in this wiki. Page may grow inbound links as `programming-languages/` expands.)
