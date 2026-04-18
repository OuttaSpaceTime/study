"""Tests for scripts.wiki.lint — all 6 lint checks."""

import json
import textwrap
from pathlib import Path

from scripts.wiki.lint import lint_wiki


def _write_page(wiki_dir: Path, rel_path: str, content: str) -> Path:
    """Write a wiki page and return its path."""
    page = wiki_dir / rel_path
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(textwrap.dedent(content))
    return page


def _write_index(wiki_dir: Path, index: dict) -> None:
    (wiki_dir / ".wiki-index.json").write_text(json.dumps(index, indent=2) + "\n")


MINIMAL_PAGE = """\
    ---
    title: "test page"
    aliases: [test alias]
    tags: [git]
    created: 2026-04-09
    ---

    # test page

    ## Section One

    Content.
"""


class TestCleanWiki:
    def test_single_page_clean(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", MINIMAL_PAGE)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": ["test alias"],
                "tags": ["git"],
                "sections": ["Section One"],
                "flashcard_ids": [],
                "created": "2026-04-09",
                "updated": "2026-04-09",
            }
        })
        errors = lint_wiki(wiki_dir)
        assert errors == []


class TestFrontmatter:
    def test_missing_frontmatter(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", "# No frontmatter\n\nContent.\n")
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("missing-frontmatter" in e for e in errors)

    def test_missing_required_field(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", """\
            ---
            title: "test"
            ---

            Content.
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "created" in e for e in errors)
        assert any("missing-field" in e and "tags" in e for e in errors)


class TestWikilinks:
    def test_broken_link(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            tags: [git]
            created: 2026-04-09
            ---

            # test page

            See [[nonexistent/page]] for details.
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("broken-link" in e for e in errors)

    def test_relative_link_flagged(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            tags: [git]
            created: 2026-04-09
            ---

            # test page

            See [[bare-link]] for details.
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("relative-link" in e or "broken-link" in e for e in errors)

    def test_valid_absolute_link(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            tags: [git]
            created: 2026-04-09
            ---

            # page a

            See [[git/page-b]] for details.
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            tags: [git]
            created: 2026-04-09
            ---

            # page b

            See [[git/page-a]] for details.
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        link_errors = [e for e in errors if "broken-link" in e or "relative-link" in e]
        assert link_errors == []


class TestOrphans:
    def test_orphan_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/page-a.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            tags: [git]
            created: 2026-04-09
            ---

            # page b

            Content with no links.
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("orphan" in e for e in errors)

    def test_single_page_not_orphan(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", MINIMAL_PAGE)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        orphan_errors = [e for e in errors if "orphan" in e]
        assert orphan_errors == []


class TestAliasCollisions:
    def test_collision_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            tags: [git]
            created: 2026-04-09
            ---

            # page a

            See [[git/page-b]].
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            tags: [git]
            created: 2026-04-09
            ---

            # page b

            See [[git/page-a]].
        """)
        _write_index(wiki_dir, {
            "git/page-a": {
                "file": "git/page-a.md",
                "title": "page a",
                "aliases": ["shared alias"],
                "tags": ["git"],
                "sections": [],
                "flashcard_ids": [],
            },
            "git/page-b": {
                "file": "git/page-b.md",
                "title": "page b",
                "aliases": ["shared alias"],
                "tags": ["git"],
                "sections": [],
                "flashcard_ids": [],
            },
        })
        errors = lint_wiki(wiki_dir)
        assert any("alias-collision" in e for e in errors)


class TestSlugMismatch:
    def test_mismatch_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/wrong-name.md", """\
            ---
            title: "Correct Name"
            tags: [git]
            created: 2026-04-09
            ---

            # Correct Name
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        assert any("slug-mismatch" in e for e in errors)

    def test_matching_slug_passes(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/correct-name.md", """\
            ---
            title: "correct name"
            tags: [git]
            created: 2026-04-09
            ---

            # correct name
        """)
        _write_index(wiki_dir, {})
        errors = lint_wiki(wiki_dir)
        slug_errors = [e for e in errors if "slug-mismatch" in e]
        assert slug_errors == []


class TestFlashcardMismatch:
    def test_mismatch_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: [test alias]
            tags: [git]
            created: 2026-04-09
            flashcard_ids: [cmne7xz9202lx, cmne7xz1y02k3]
            ---

            # test page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": ["test alias"],
                "tags": ["git"],
                "sections": ["Section One"],
                "flashcard_ids": [],
            }
        })
        errors = lint_wiki(wiki_dir)
        assert any("flashcard-mismatch" in e for e in errors)

    def test_matching_ids_passes(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: [test alias]
            tags: [git]
            created: 2026-04-09
            flashcard_ids: [abc123, def456]
            ---

            # test page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": ["test alias"],
                "tags": ["git"],
                "sections": ["Section One"],
                "flashcard_ids": ["abc123", "def456"],
            }
        })
        errors = lint_wiki(wiki_dir)
        fc_errors = [e for e in errors if "flashcard-mismatch" in e]
        assert fc_errors == []
