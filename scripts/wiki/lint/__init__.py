"""Wiki linter.

structure.py holds the errors (frontmatter, links, slugs, index agreement), prose.py
the warnings (style, heading case, density), runner.py runs both and applies
`lint_ignore`. The names other code imports stay available from here.
"""

from scripts.wiki.lint.page import ParsedPage
from scripts.wiki.lint.runner import lint_wiki, main
from scripts.wiki.lint.structure import (
    ALLOWED_FIELDS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    RETIRED_FIELDS,
)

__all__ = [
    "ALLOWED_FIELDS",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "RETIRED_FIELDS",
    "ParsedPage",
    "lint_wiki",
    "main",
]
