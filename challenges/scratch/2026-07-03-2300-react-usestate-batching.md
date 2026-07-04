---
kind: write-code
env: react
questions:
- Why does the counter go up by 1 even though setCount is called three times?
- What is the minimal change that makes all three increments count?
created: 2026-07-03
---

## Brief

This button should add 3 per click but adds 1. Fix the handler so all three increments land, then explain why the original version collapses to one.

## Stub

```jsx
function Counter() {
  const [count, setCount] = React.useState(0);
  const addThree = () => {
    setCount(count + 1);
    setCount(count + 1);
    setCount(count + 1);
  };
  return (
    <button onClick={addThree} style={{ fontSize: "2rem", padding: "1rem" }}>
      count: {count}
    </button>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Counter />);
```

## Solution

```jsx
function Counter() {
  const [count, setCount] = React.useState(0);
  const addThree = () => {
    setCount((c) => c + 1);
    setCount((c) => c + 1);
    setCount((c) => c + 1);
  };
  return (
    <button onClick={addThree} style={{ fontSize: "2rem", padding: "1rem" }}>
      count: {count}
    </button>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<Counter />);
```
