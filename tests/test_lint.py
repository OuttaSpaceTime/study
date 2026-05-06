"""Tests for scripts.wiki.lint — all checks plus severity split."""

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
    updated: 2026-04-09
    source_skill: study-walkthrough
    probe_sections: [Section One]
    ---

    # test page

    ## Section One

    Content.
"""


class TestCleanWiki:
    def test_single_page_clean(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/git-index.md", textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            ---

            # Git Index

            ## Pages

            - [[git/test-page]]
        """))
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": ["test alias"],
                "tags": ["git"],
                "sections": ["Section One"],
                "flashcard_ids": [],
                "probe_sections": ["Section One"],
                "last_probed": [],
                "created": "2026-04-09",
                "updated": "2026-04-09",
            }
        })
        errors, warnings = lint_wiki(wiki_dir)
        assert errors == []
        assert warnings == []


class TestFrontmatter:
    def test_missing_frontmatter(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", "# No frontmatter\n\nContent.\n")
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-frontmatter" in e for e in errors)

    def test_missing_required_field(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", """\
            ---
            title: "test"
            ---

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        for field in ("created", "tags", "aliases", "updated", "source_skill"):
            assert any("missing-field" in e and field in e for e in errors), (
                f"expected missing-field for {field}"
            )

    def test_missing_aliases_is_error(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", """\
            ---
            title: "test"
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "aliases" in e for e in errors)

    def test_missing_updated_is_error(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", """\
            ---
            title: "test"
            aliases: []
            tags: [git]
            created: 2026-04-09
            source_skill: study-walkthrough
            ---
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "updated" in e for e in errors)

    def test_missing_source_skill_is_error(self, wiki_dir: Path):
        _write_page(wiki_dir, "bad.md", """\
            ---
            title: "test"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            ---
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "source_skill" in e for e in errors)


class TestWikilinks:
    def test_broken_link(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # test page

            See [[nonexistent/page]] for details.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("broken-link" in e for e in errors)

    def test_relative_link_flagged(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # test page

            See [[bare-link]] for details.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("relative-link" in e or "broken-link" in e for e in errors)

    def test_valid_absolute_link(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # page a

            See [[git/page-b]] for details.
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # page b

            See [[git/page-a]] for details.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        link_errors = [e for e in errors if "broken-link" in e or "relative-link" in e]
        assert link_errors == []

    def test_link_with_heading_anchor_resolves(self, wiki_dir: Path):
        """[[git/page-b#section]] should resolve if git/page-b.md exists."""
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            See [[git/page-b#section-one]] for details.
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            [[git/page-a]]
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        link_errors = [e for e in errors if "broken-link" in e or "relative-link" in e]
        assert link_errors == [], f"unexpected link errors: {link_errors}"

    def test_link_with_display_text_resolves(self, wiki_dir: Path):
        """[[git/page-b|display text]] (pipe alias) should resolve."""
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            See [[git/page-b|Page B]].
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            [[git/page-a]]
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        link_errors = [e for e in errors if "broken-link" in e or "relative-link" in e]
        assert link_errors == []

    def test_fenced_code_wikilinks_ignored(self, wiki_dir: Path):
        """Wikilinks inside fenced code blocks should not be linted."""
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            See [[git/page-b]] for real.

            ```
            Example of wiki syntax: [[nonexistent/page]]
            ```
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            [[git/page-a]]
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert not any("nonexistent" in e for e in errors), (
            f"wikilinks in fenced code were linted: {errors}"
        )

    def test_inline_code_wikilinks_ignored(self, wiki_dir: Path):
        """Wikilinks inside inline code should not be linted."""
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            Real link: [[git/page-b]].

            Inline example: `[[nonexistent/page]]`.
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            [[git/page-a]]
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert not any("nonexistent" in e for e in errors)

    def test_image_embed_not_flagged(self, wiki_dir: Path):
        """![[image.png]] embeds should not trigger broken-link / relative-link."""
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            See [[git/page-b]] for details.

            ![[some-image.png]]
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            [[git/page-a]]
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert not any("some-image" in e for e in errors)


class TestOrphans:
    def test_orphan_is_warning_not_error(self, wiki_dir: Path):
        """Orphans should appear in warnings, not errors."""
        _write_page(wiki_dir, "git/page-a.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            Content with no links.
        """)
        _write_index(wiki_dir, {})
        errors, warnings = lint_wiki(wiki_dir)
        assert any("orphan" in w for w in warnings)
        assert not any("orphan" in e for e in errors)

    def test_allow_orphan_suppresses_warning(self, wiki_dir: Path):
        """Pages with `allow_orphan: true` should not warn."""
        _write_page(wiki_dir, "git/page-a.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            allow_orphan: true
            ---

            Intentionally standalone.
        """)
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        orphans = [w for w in warnings if "page-b" in w and "orphan" in w]
        assert orphans == [], f"allow_orphan did not suppress: {orphans}"

    def test_self_link_does_not_count_as_inbound(self, wiki_dir: Path):
        """A page linking only to itself is still an orphan."""
        _write_page(wiki_dir, "git/page-a.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            Self: [[git/page-b]].
        """)
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        assert any("page-b" in w and "orphan" in w for w in warnings)

    def test_single_page_not_orphan(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", MINIMAL_PAGE)
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        orphan_warnings = [w for w in warnings if "orphan" in w]
        assert orphan_warnings == []


class TestAliasCollisions:
    def test_collision_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/page-a.md", """\
            ---
            title: "page a"
            aliases: [shared alias]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            See [[git/page-b]].
        """)
        _write_page(wiki_dir, "git/page-b.md", """\
            ---
            title: "page b"
            aliases: [shared alias]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

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
        errors, _ = lint_wiki(wiki_dir)
        assert any("alias-collision" in e for e in errors)


class TestSlugMismatch:
    def test_mismatch_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/wrong-name.md", """\
            ---
            title: "Correct Name"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # Correct Name
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("slug-mismatch" in e for e in errors)

    def test_matching_slug_passes(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/correct-name.md", """\
            ---
            title: "correct name"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # correct name
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        slug_errors = [e for e in errors if "slug-mismatch" in e]
        assert slug_errors == []


class TestProbeSections:
    """Probe section lint rules for SRS wiki review."""

    def test_probe_section_matches_heading(self, wiki_dir: Path):
        """probe_sections entries must correspond to actual H2 headings."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["Nonexistent Section"]
            ---

            # test page

            ## Real Section

            Content.
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["Real Section"],
                "flashcard_ids": [],
                "probe_sections": ["Nonexistent Section"],
                "last_probed": [],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        assert any("probe-section-unresolved" in e for e in errors), (
            f"expected probe-section-unresolved: {errors}"
        )

    def test_probe_section_normalized_match(self, wiki_dir: Path):
        """Matching is case-insensitive and ignores trailing punctuation."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["when to use"]
            last_probed: ["when to use"]
            ---

            # test page

            ## When to use?

            Content.
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["When to use?"],
                "flashcard_ids": [],
                "probe_sections": ["when to use"],
                "last_probed": ["when to use"],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        probe_errors = [e for e in errors if "probe-" in e]
        assert probe_errors == [], f"unexpected probe errors: {probe_errors}"

    def test_last_probed_must_match_probe_sections(self, wiki_dir: Path):
        """If last_probed is non-empty, it must contain exactly the same elements as probe_sections."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["A", "B"]
            last_probed: ["A"]
            ---

            # test page

            ## A

            ## B
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["A", "B"],
                "flashcard_ids": [],
                "probe_sections": ["A", "B"],
                "last_probed": ["A"],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        assert any("probe-rotation-drift" in e for e in errors), (
            f"expected probe-rotation-drift: {errors}"
        )

    def test_last_probed_empty_is_ok(self, wiki_dir: Path):
        """Empty last_probed is valid — means not yet reviewed."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["A", "B"]
            last_probed: []
            ---

            # test page

            ## A

            ## B
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["A", "B"],
                "flashcard_ids": [],
                "probe_sections": ["A", "B"],
                "last_probed": [],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        probe_errors = [e for e in errors if "probe-" in e]
        assert probe_errors == [], f"unexpected probe errors: {probe_errors}"

    def test_all_pages_require_probe_sections(self, wiki_dir: Path):
        """Every wiki page must declare non-empty probe_sections."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # test page

            ## A
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["A"],
                "flashcard_ids": [],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        assert any("probe-sections-missing" in e for e in errors), (
            f"expected probe-sections-missing: {errors}"
        )

    def test_probe_sections_index_drift_detected(self, wiki_dir: Path):
        """Frontmatter probe_sections must match index probe_sections."""
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["A", "B"]
            last_probed: ["A", "B"]
            ---

            # test page

            ## A

            ## B
        """)
        _write_index(wiki_dir, {
            "git/test-page": {
                "file": "git/test-page.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["A", "B"],
                "flashcard_ids": [],
                "probe_sections": ["A"],
                "last_probed": ["A", "B"],
            }
        })
        errors, _ = lint_wiki(wiki_dir)
        assert any("probe-index-drift" in e for e in errors), (
            f"expected probe-index-drift: {errors}"
        )


class TestFlashcardMismatch:
    def test_mismatch_detected(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: [test alias]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
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
        errors, _ = lint_wiki(wiki_dir)
        assert any("flashcard-mismatch" in e for e in errors)

    def test_matching_ids_passes(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", """\
            ---
            title: "test page"
            aliases: [test alias]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
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
        errors, _ = lint_wiki(wiki_dir)
        fc_errors = [e for e in errors if "flashcard-mismatch" in e]
        assert fc_errors == []
