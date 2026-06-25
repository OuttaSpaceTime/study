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
    flashcard_ids: []
    next_review: '2026-05-01'
    review_interval: 3
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
            flashcard_ids: []
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

    def test_missing_flashcard_ids_is_error(self, wiki_dir: Path):
        """flashcard_ids is required on all pages (even index)."""
        _write_page(wiki_dir, "git/git-index.md", """\
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
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "flashcard_ids" in e for e in errors)

    def test_missing_next_review_on_content_page_is_error(self, wiki_dir: Path):
        """next_review is required on non-index content pages."""
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            review_interval: 3
            probe_sections: [Section One]
            allow_orphan: true
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "next_review" in e for e in errors)

    def test_missing_next_review_on_index_page_not_error(self, wiki_dir: Path):
        """next_review, review_interval are not required on *-index.md pages."""
        _write_page(wiki_dir, "git/git-index.md", """\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            ---

            # Git Index

            ## Pages
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        content_field_errors = [
            e for e in errors
            if any(f in e for f in ("next_review", "review_interval"))
        ]
        assert content_field_errors == [], f"index page should not require content fields: {content_field_errors}"

    def test_missing_review_interval_on_content_page_is_error(self, wiki_dir: Path):
        """review_interval is required on non-index content pages."""
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            next_review: '2026-05-01'
            probe_sections: [Section One]
            allow_orphan: true
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "review_interval" in e for e in errors)


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


class TestMocFrontmatter:
    """MOC pages have stricter frontmatter rules than content pages."""

    def _moc(self, body_extra_meta: str = "", body: str = "## Pages\n") -> str:
        return textwrap.dedent(f"""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            {body_extra_meta}---

            # Git Index

            {body}
        """)

    def test_clean_moc_passes(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/git-index.md", self._moc())
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        moc_errors = [e for e in errors if "moc-" in e]
        assert moc_errors == [], f"clean MOC should pass: {moc_errors}"

    def test_missing_moc_tag_is_error(self, wiki_dir: Path):
        page = textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            ---

            # Git Index

            ## Pages
        """)
        _write_page(wiki_dir, "git/git-index.md", page)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("moc-tag-missing" in e for e in errors), errors

    def test_missing_folder_tag_is_error(self, wiki_dir: Path):
        page = textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            ---

            # Git Index

            ## Pages
        """)
        _write_page(wiki_dir, "git/git-index.md", page)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("moc-folder-tag-missing" in e for e in errors), errors

    def test_missing_allow_orphan_is_error(self, wiki_dir: Path):
        page = textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            ---

            # Git Index

            ## Pages
        """)
        _write_page(wiki_dir, "git/git-index.md", page)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("moc-allow-orphan-missing" in e for e in errors), errors

    def test_review_field_on_moc_is_error(self, wiki_dir: Path):
        page = textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: manual
            flashcard_ids: []
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            next_review: 2026-05-01
            review_interval: 3
            ---

            # Git Index

            ## Pages
        """)
        _write_page(wiki_dir, "git/git-index.md", page)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        for field in ("next_review", "review_interval"):
            assert any("moc-forbidden-field" in e and field in e for e in errors), (
                f"expected moc-forbidden-field for {field}: {errors}"
            )


class TestAliases:
    def test_single_letter_alias_is_error(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/test-page.md", textwrap.dedent("""\
            ---
            title: "test page"
            aliases: ["x"]
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            depth: 1
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: [Section One]
            allow_orphan: true
            ---

            # test page

            ## Section One

            Content.
        """))
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("alias-too-short" in e for e in errors), errors


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


# A minimal single-page setup for prose quality tests: allow_orphan suppresses orphan
# warning so we only see prose-quality hits.
_PROSE_PAGE_TEMPLATE = """\
    ---
    title: "{title}"
    aliases: []
    tags: [git]
    created: 2026-04-09
    updated: 2026-04-09
    source_skill: study-walkthrough
    probe_sections: [Section One]
    allow_orphan: true
    ---

    # {title}

    ## Section One

    {body}
"""


class TestProseQuality:
    def test_em_dash_flagged(self, wiki_dir: Path):
        """Page body containing an em dash outside a code block → prose-quality warning."""
        _write_page(wiki_dir, "git/em-dash.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="em dash",
                body="The function validates the token — it raises if invalid.",
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        prose = [w for w in warnings if "prose-quality" in w and "em-dash" in w]
        assert len(prose) == 1, f"expected one em-dash warning, got: {warnings}"

    def test_in_order_to_flagged(self, wiki_dir: Path):
        """Page body containing 'in order to' → prose-quality warning."""
        _write_page(wiki_dir, "git/wordy.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="wordy",
                body="Call this function in order to parse the response.",
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        prose = [w for w in warnings if "prose-quality" in w and "in-order-to" in w]
        assert len(prose) == 1, f"expected one in-order-to warning, got: {warnings}"

    def test_em_dash_in_code_block_not_flagged(self, wiki_dir: Path):
        """Em dash only inside a fenced code block → no prose-quality warning."""
        body = "```\nresult — value\n```\n\nNo em dash outside the fence."
        _write_page(wiki_dir, "git/code-dash.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="code dash",
                body=body,
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        prose = [w for w in warnings if "prose-quality" in w and "em-dash" in w]
        assert prose == [], f"em dash in code block should not warn, got: {warnings}"

    def test_clean_page_no_warning(self, wiki_dir: Path):
        """Page with none of the banned patterns → no prose-quality warnings."""
        _write_page(wiki_dir, "git/clean.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="clean",
                body="Use this function to parse the response. It raises on error.",
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        prose = [w for w in warnings if "prose-quality" in w]
        assert prose == [], f"expected no prose-quality warnings, got: {warnings}"


class TestColonConnectors:
    def test_mid_line_prose_colon_flagged(self, wiki_dir: Path):
        """': ' connecting two prose clauses → prose-colon warning."""
        _write_page(wiki_dir, "git/colon.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="colon",
                body="The function validates the token: it raises if invalid.",
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        assert any("prose-colon" in w for w in warnings), f"expected prose-colon: {warnings}"

    def test_heading_colon_not_flagged(self, wiki_dir: Path):
        """Colon in a heading line → not flagged."""
        _write_page(wiki_dir, "git/heading-colon.md", textwrap.dedent("""\
            ---
            title: "heading colon"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            probe_sections: ["What pick does: return first row"]
            allow_orphan: true
            ---

            # heading colon

            ## What pick does: return first row

            Clean prose without connectors.
        """))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"heading colon should not warn: {warnings}"

    def test_list_item_colon_not_flagged(self, wiki_dir: Path):
        """Colon separating term from description in a list item → not flagged."""
        _write_page(wiki_dir, "git/list-colon.md", """\
---
title: "list colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# list colon

## Section One

- **max-age**: how long the browser remembers the rule
- **preload**: opts into the preload list
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"list colon should not warn: {warnings}"

    def test_eol_colon_before_list_not_flagged(self, wiki_dir: Path):
        """End-of-line colon followed by a list → not flagged."""
        _write_page(wiki_dir, "git/eol-list.md", """\
---
title: "eol list"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# eol list

## Section One

Three options:

- first
- second
- third
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"eol colon before list should not warn: {warnings}"

    def test_eol_colon_before_code_not_flagged(self, wiki_dir: Path):
        """End-of-line colon followed by a code fence → not flagged."""
        _write_page(wiki_dir, "git/eol-code.md", """\
---
title: "eol code"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# eol code

## Section One

Example:

```ruby
puts 'hello'
```
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"eol colon before code should not warn: {warnings}"

    def test_eol_colon_before_prose_flagged(self, wiki_dir: Path):
        """End-of-line colon followed by a plain prose line → flagged."""
        _write_page(wiki_dir, "git/eol-prose.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(
                title="eol prose",
                body="The key rule:\n\nAlways validate before writing.",
            )
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        assert any("prose-colon" in w for w in warnings), f"expected prose-colon: {warnings}"

    def test_colon_in_code_block_not_flagged(self, wiki_dir: Path):
        """': ' inside a fenced code block → not flagged."""
        _write_page(wiki_dir, "git/code-colon.md", """\
---
title: "code colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# code colon

## Section One

```ruby
user = User.find_by(email: params[:email])
```
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon in code block should not warn: {warnings}"

    def test_colon_in_quoted_string_not_flagged(self, wiki_dir: Path):
        """': ' inside a quoted string → not flagged."""
        _write_page(wiki_dir, "git/quoted-colon.md", """\
---
title: "quoted colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# quoted colon

## Section One

The method returns "type: value" format for all responses.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon in quoted string should not warn: {warnings}"

    def test_colon_in_backtick_not_flagged(self, wiki_dir: Path):
        """': ' inside double-backtick inline code → not flagged."""
        _write_page(wiki_dir, "git/backtick-colon.md", """\
---
title: "backtick colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# backtick colon

## Section One

Pass ``content_type: application/json`` in the header.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon in backtick code should not warn: {warnings}"

    def test_colon_inside_link_brackets_not_flagged(self, wiki_dir: Path):
        """': ' inside [link text: something] → not flagged."""
        _write_page(wiki_dir, "git/link-colon-inside.md", """\
---
title: "link colon inside"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# link colon inside

## Section One

See [OWAS: asdfasdsf] for details.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon inside link brackets should not warn: {warnings}"

    def test_colon_after_wikilink_not_flagged(self, wiki_dir: Path):
        """'[[target]]: description' in prose → not flagged."""
        _write_page(wiki_dir, "git/wikilink-colon.md", """\
---
title: "wikilink colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# wikilink colon

## Section One

[[git/git-restore]]: restores working tree files without touching the index.
""")
        _write_index(wiki_dir, {"git/git-restore": {"file": "git/git-restore.md", "title": "git restore", "aliases": [], "sections": [], "tags": [], "flashcard_ids": [], "probe_sections": [], "last_probed": [], "created": "2026-04-09", "updated": "2026-04-09"}})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon after wikilink should not warn: {warnings}"

    def test_colon_after_md_link_not_flagged(self, wiki_dir: Path):
        """'[text](url): description' in prose → not flagged."""
        _write_page(wiki_dir, "git/mdlink-colon.md", """\
---
title: "mdlink colon"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# mdlink colon

## Section One

[OWASP CSRF Cheat Sheet](https://owasp.org/csrf): canonical defense taxonomy.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        colon_warns = [w for w in warnings if "prose-colon" in w]
        assert colon_warns == [], f"colon after markdown link should not warn: {warnings}"


class TestSentenceFragments:
    def test_short_sentence_mid_line_flagged(self, wiki_dir: Path):
        """≤3-word sentence followed by lowercase continuation → sentence-fragment warning."""
        _write_page(wiki_dir, "git/fragment.md", """\
---
title: "fragment"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# fragment

## Section One

The practical takeaway. **for long-context requests the cache can exceed the weights.**
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert len(frags) == 1, f"expected one sentence-fragment warning, got: {warnings}"

    def test_short_sentence_uppercase_continuation_not_flagged(self, wiki_dir: Path):
        """Short sentence (≤3 words) followed by uppercase continuation → no warning."""
        _write_page(wiki_dir, "git/ok-sentence.md", """\
---
title: "ok sentence"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# ok sentence

## Section One

Both are bad. The fix is a convention, not a runtime feature.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert frags == [], f"short sentence before uppercase should not warn: {warnings}"

    def test_terminal_short_sentence_not_flagged(self, wiki_dir: Path):
        """A short sentence at end of line (no continuation) is not flagged."""
        _write_page(wiki_dir, "git/terminal-short.md", """\
---
title: "terminal short"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# terminal short

## Section One

A detailed explanation of the concept ends here. Both are bad.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert frags == [], f"terminal short sentence should not warn: {warnings}"

    def test_short_sentence_in_code_not_flagged(self, wiki_dir: Path):
        """Short sentence inside a code block → not flagged."""
        _write_page(wiki_dir, "git/code-fragment.md", """\
---
title: "code fragment"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# code fragment

## Section One

```
# Short. Comment here for the reader.
```

Normal prose with four or more words per sentence.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert frags == [], f"short sentence in code block should not warn: {warnings}"

    def test_inline_code_at_sentence_start_not_flagged(self, wiki_dir: Path):
        """Inline code token at start of next sentence (e.g. `WHERE`) must not lose its case info."""
        _write_page(wiki_dir, "git/inline-code-start.md", """\
---
title: "inline code start"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# inline code start

## Section One

Any comparison involving `NULL` returns `UNKNOWN`. Including `NULL = NULL`. `WHERE` only keeps rows where the predicate is `TRUE`.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert frags == [], f"inline code at sentence start should not warn: {warnings}"

    def test_abbreviation_period_not_flagged(self, wiki_dir: Path):
        """Period after abbreviation like 'vs.' must not be treated as sentence-ending."""
        _write_page(wiki_dir, "git/abbrev-period.md", """\
---
title: "abbrev period"
aliases: []
tags: [git]
created: 2026-04-09
updated: 2026-04-09
source_skill: study-walkthrough
probe_sections: [Section One]
allow_orphan: true
---

# abbrev period

## Section One

Two changes vs. a regular unique index:

- The index stores only matching rows.
""")
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        frags = [w for w in warnings if "sentence-fragment" in w]
        assert frags == [], f"abbreviation period should not warn: {warnings}"


class TestProbeFiles:
    """Probe files in probes/<topic>/ must point to a real wiki page via `wiki:` frontmatter."""

    def _write_target_page(self, wiki_dir: Path) -> None:
        _write_page(wiki_dir, "compilers/compilers.md", MINIMAL_PAGE)
        _write_index(wiki_dir, {
            "compilers/compilers": {
                "file": "compilers/compilers.md",
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

    def _write_probe(self, probes_dir: Path, rel: str, frontmatter: str) -> None:
        path = probes_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(frontmatter))

    def test_probe_with_resolved_wiki_clean(self, tmp_path: Path, wiki_dir: Path):
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "compilers/p1.md", """\
            ---
            topic: compilers
            wiki: compilers/compilers
            created: 2026-05-05 08:10
            ---

            ## Prediction
            x

            ## Command
            ```bash
            true
            ```

            ## Output
            ```
            ```

            ## Takeaway
            x
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        probe_errors = [e for e in errors if "probe-wiki" in e]
        assert probe_errors == [], f"unexpected probe errors: {probe_errors}"

    def test_probe_with_empty_wiki_field_is_error(self, tmp_path: Path, wiki_dir: Path):
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "compilers/p1.md", """\
            ---
            topic: compilers
            wiki:
            created: 2026-05-05 08:10
            ---

            ## Prediction
            x
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        assert any("probe-wiki-missing" in e for e in errors), (
            f"expected probe-wiki-missing: {errors}"
        )

    def test_probe_with_missing_wiki_field_is_error(self, tmp_path: Path, wiki_dir: Path):
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "compilers/p1.md", """\
            ---
            topic: compilers
            created: 2026-05-05 08:10
            ---

            ## Prediction
            x
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        assert any("probe-wiki-missing" in e for e in errors), (
            f"expected probe-wiki-missing: {errors}"
        )

    def test_probe_with_unresolved_wiki_path_is_error(self, tmp_path: Path, wiki_dir: Path):
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "compilers/p1.md", """\
            ---
            topic: compilers
            wiki: programming-languages/does-not-exist
            created: 2026-05-05 08:10
            ---

            ## Prediction
            x
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        assert any("probe-wiki-unresolved" in e for e in errors), (
            f"expected probe-wiki-unresolved: {errors}"
        )

    def test_probe_with_md_suffix_is_unresolved(self, tmp_path: Path, wiki_dir: Path):
        """`wiki: foo.md` is non-canonical — wiki keys never carry `.md`.

        Why this matters: `scripts/wiki/probes.py:for_wiki()` uses exact equality, so
        a `.md`-suffixed probe wiki ref is silently invisible to `scripts/wiki-probes`.
        Lint must reject the non-canonical form so the two stay in sync.
        """
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "compilers/p1.md", """\
            ---
            topic: compilers
            wiki: compilers/compilers.md
            created: 2026-05-05 08:10
            ---

            ## Prediction
            x
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        assert any("probe-wiki-unresolved" in e for e in errors), (
            f"expected probe-wiki-unresolved on .md suffix: {errors}"
        )

    def test_template_and_readme_skipped(self, tmp_path: Path, wiki_dir: Path):
        self._write_target_page(wiki_dir)
        probes_dir = tmp_path / "probes"
        self._write_probe(probes_dir, "_template.md", """\
            ---
            topic: <topic-slug>
            wiki:
            created: YYYY-MM-DD HH:MM
            ---

            ## Prediction
        """)
        self._write_probe(probes_dir, "README.md", "# Probes\n")
        self._write_probe(probes_dir, "compilers/_scratch.md", """\
            ---
            topic: compilers
            wiki:
            ---
        """)
        errors, _ = lint_wiki(wiki_dir, probes_dir=probes_dir)
        probe_errors = [e for e in errors if "probe-wiki" in e]
        assert probe_errors == [], f"template/readme/_-prefixed should be skipped: {probe_errors}"

    def test_no_probes_dir_no_error(self, wiki_dir: Path):
        """Lint must not fail when the probes directory does not exist."""
        errors, _ = lint_wiki(wiki_dir, probes_dir=wiki_dir.parent / "no-such-probes")
        probe_errors = [e for e in errors if "probe-wiki" in e]
        assert probe_errors == [], f"missing probes dir should be silent: {probe_errors}"
