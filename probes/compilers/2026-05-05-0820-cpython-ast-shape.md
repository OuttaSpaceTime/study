---
topic: compilers
session: 2026-05-05-walkthrough
wiki: programming-languages/compilers-and-interpreters
created: 2026-05-05 08:20
---

## Prediction

The AST root for `print("hi")` will be the `print` node — the function call sits at the top.

## Command

```bash
python3 -c "import ast; print(ast.dump(ast.parse('print(\"hi\")'), indent=2))"
```

## Output

```
Module(
  body=[
    Expr(
      value=Call(
        func=Name(id='print', ctx=Load()),
        args=[
          Constant(value='hi')],
        keywords=[]))],
  type_ignores=[])
```

## Takeaway

Wrong prediction. The root is always `Module(body=[...])` regardless of how short the source is — even a single expression like `print("hi")` gets wrapped: `Module → Expr → Call → (Name + Constant)`. The parser thinks in terms of "a file is a list of statements," not "what did the user type." `Expr` is the wrapper for "this statement is a bare expression with no side-effect statement around it." This explains why later compilation walks `Module.body` and emits bytecode for each entry in order — the structure is what makes the codegen loop possible.
