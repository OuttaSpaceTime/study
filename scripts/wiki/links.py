"""Wikilinks and the code they must not be read from.

One home for these rules: lint checks links with them, and the Omvida app
(~/Code/omvida, backend/omvida_backend/wiki.py) builds its link graph with them,
so a link lint calls broken is never one the app draws, or the reverse.
Resolving a bare `[[name]]` by its slug stays with each reader: lint rejects it
(relative-link), while the app and the wiki-viewer resolve it the way Obsidian
does.
"""

from __future__ import annotations

import re

FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"``[^`\n]+``|`[^`\n]+`")
# Not preceded by `!` (an embed). Captures the target before any `#anchor` or `|display`.
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def strip_code(body: str) -> str:
    """Remove fenced and inline code, where `[[...]]` is not a link."""
    return INLINE_CODE_RE.sub("", FENCED_CODE_RE.sub("", body))


def link_targets(body: str) -> list[str]:
    """The targets of a page's wikilinks, in order, embeds and code excluded."""
    return [t.strip() for t in WIKILINK_RE.findall(strip_code(body)) if t.strip()]
