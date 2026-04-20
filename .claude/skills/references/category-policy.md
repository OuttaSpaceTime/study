# Category Policy

Shared across `/study`, `/study-flashcard`, `/study-walkthrough`. Every card and every wiki page carries a **category ∈ {work, personal}** — mixed state is not supported anywhere.

## Closed set

Only `work` or `personal`. Never invent a third value, never pass an empty string, never call MCP with a category the user hasn't explicitly chosen.

## Resolution order (pick the first rule that applies)

1. **Explicit flag** — if the skill was invoked with `-c work` / `-c personal`, use it without asking.
2. **Inheritance** — if the current action extends an existing artifact that already carries a category, inherit it. Specifically:
   - Extending a wiki page → use that page's frontmatter `category`.
   - Chaining from another categorized skill (e.g. `/study-walkthrough` → `/study-flashcard`) → pass the category through so the downstream skill does not re-ask.
3. **Prompt once** — otherwise ask the developer: "work or personal?" Accept only those two answers; if the reply is ambiguous, default to `work` and state that default.

## Where the value lands

- Flashcards → `create_card({ category })` / `update_card({ category })`.
- Sessions → `start_session({ category })`; `adjust_session({ focusCategory })` narrows mid-session.
- Wiki pages → `category:` frontmatter field (required by lint).
- Wiki due queries → `scripts/wiki-due --category <cat>`.
