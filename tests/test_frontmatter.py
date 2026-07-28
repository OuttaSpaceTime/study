"""Tests for scripts.wiki.frontmatter — parse/dump YAML frontmatter, slugify."""

import textwrap

from scripts.wiki.frontmatter import parse_frontmatter, slugify


class TestParseFrontmatter:
    def test_parse_real_page(self):
        content = textwrap.dedent("""\
            ---
            title: "git restore"
            aliases: [git restore command, restore files git]
            tags: [git, version-control]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: [cmne7xz9202lx0msonsbfhp3j, cmne7xz1y02k30msouw64srcz]
            last_deepened: 2026-04-09
            next_review: 2026-04-12
            review_interval: 3
            ---

            # git restore

            Some body content.
        """)
        meta, body = parse_frontmatter(content)
        assert meta["title"] == "git restore"
        assert meta["aliases"] == ["git restore command", "restore files git"]
        assert meta["tags"] == ["git", "version-control"]
        assert meta["created"] == "2026-04-09"
        assert meta["updated"] == "2026-04-09"
        assert meta["next_review"] == "2026-04-12"
        assert meta["review_interval"] == 3
        assert "# git restore" in body

    def test_flashcard_ids_are_strings(self):
        content = textwrap.dedent("""\
            ---
            title: "test"
            flashcard_ids: [cmne7xz9202lx0msonsbfhp3j, cmne7xz1y02k30msouw64srcz]
            tags: [git]
            created: 2026-04-09
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert isinstance(meta["flashcard_ids"], list)
        assert all(isinstance(fid, str) for fid in meta["flashcard_ids"])
        assert meta["flashcard_ids"][0] == "cmne7xz9202lx0msonsbfhp3j"

    def test_numeric_flashcard_ids_become_strings(self):
        content = textwrap.dedent("""\
            ---
            title: "test"
            flashcard_ids: [101, 202]
            tags: [js]
            created: 2026-04-09
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert meta["flashcard_ids"] == ["101", "202"]

    def test_only_flashcard_ids_are_coerced_to_strings(self):
        content = textwrap.dedent("""\
            ---
            title: "test"
            tags: [test]
            created: 2026-04-09
            review_interval: 38
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert meta["review_interval"] == 38

    def test_empty_flashcard_ids(self):
        content = textwrap.dedent("""\
            ---
            title: "test"
            flashcard_ids: []
            tags: [misc]
            created: 2026-04-09
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert meta["flashcard_ids"] == []

    def test_dates_are_iso_strings(self):
        content = textwrap.dedent("""\
            ---
            title: "test"
            created: 2026-04-09
            updated: 2026-04-09
            next_review: 2026-04-12
            tags: [test]
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert isinstance(meta["created"], str)
        assert meta["created"] == "2026-04-09"
        assert isinstance(meta["next_review"], str)

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome content.\n"
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_malformed_frontmatter(self):
        content = "---\ntitle: test\nno closing delimiter\n"
        meta, body = parse_frontmatter(content)
        assert meta == {}
        assert body == content

    def test_missing_optional_fields(self):
        content = textwrap.dedent("""\
            ---
            title: "minimal page"
            tags: [test]
            created: 2026-04-09
            ---

            Body.
        """)
        meta, _ = parse_frontmatter(content)
        assert meta["title"] == "minimal page"
        assert "flashcard_ids" not in meta
        assert "next_review" not in meta


class TestSlugify:
    def test_basic(self):
        assert slugify("git restore") == "git-restore"

    def test_special_chars(self):
        assert slugify("What's New?") == "what-s-new"

    def test_consecutive_spaces(self):
        assert slugify("a   b") == "a-b"

    def test_leading_trailing(self):
        assert slugify("--hello--") == "hello"

    def test_uppercase(self):
        assert slugify("Hello World") == "hello-world"

    def test_numbers(self):
        assert slugify("HTTP 2.0 Guide") == "http-2-0-guide"
