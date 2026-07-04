---
wiki: software-design/judging-abstractions
section: Leaky abstractions and the working-vs-learning cost
kind: predict-output
env: python312
questions:
- What implementation detail beneath lru_cache leaked through its interface here?
- How does this demonstrate that an abstraction saves working time but not learning time?
created: 2026-07-03
---

## Brief

lru_cache hides memoization behind one decorator. Predict what happens when the cached function receives a tuple and then a list.

## Stub

```python
from functools import lru_cache

@lru_cache
def total(items):
    return sum(items)

print(total((1, 2, 3)))
try:
    print(total([1, 2, 3]))
except TypeError as e:
    print("leak:", e)
```

## Solution

```python
from functools import lru_cache

@lru_cache
def total(items):
    return sum(items)

print(total((1, 2, 3)))
try:
    print(total([1, 2, 3]))
except TypeError as e:
    print("leak:", e)
```

## Expected Output

```
6
leak: unhashable type: 'list'
```
