---
name: Study log wikilink rules
description: Session logs must not backtick wikilinks and must not create wikilinks to non-existent pages
type: feedback
---

Two rules for session logs in `logs/`:

1. Never wrap `[[wiki/path]]` references in backticks -- backticks prevent Obsidian from rendering them as clickable wikilinks. Write `[[rails/index-with]]` not `` `[[rails/index-with]]` ``.

2. Never create wikilinks for things that aren't actual wiki pages. Lapse names, card titles, and other plain-text items should be written as plain text, not as `[[links]]`. Only link to pages that exist in the wiki index.

**Why:** Backticked links break Obsidian navigation. Phantom wikilinks pollute the graph and create false broken-link warnings.

**How to apply:** When writing session logs in `/study`, check the wiki index before creating any `[[link]]`. If the target doesn't exist as a wiki page, write it as plain text.
