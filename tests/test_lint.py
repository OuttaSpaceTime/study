"""Tests for scripts.wiki.lint — all checks plus severity split."""

import json
import textwrap
from pathlib import Path

import pytest

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
        """flashcard_ids is required on all pages."""
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("missing-field" in e and "flashcard_ids" in e for e in errors)

    def test_scheduling_field_on_content_page_is_error(self, wiki_dir: Path):
        """Retired scheduling fields must not reappear on any page."""
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
            review_interval: 3
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        for field in ("next_review", "review_interval"):
            assert any("forbidden-field" in e and field in e for e in errors), errors

    def test_last_deepened_is_error(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            last_deepened: 2026-04-09
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("forbidden-field" in e and "last_deepened" in e for e in errors), errors

    def test_allow_orphan_is_error(self, wiki_dir: Path):
        """The orphan check is gone, so its opt-out is a retired field."""
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            allow_orphan: true
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("forbidden-field" in e and "allow_orphan" in e for e in errors), errors

    def test_unknown_field_is_error(self, wiki_dir: Path):
        """The schema is closed, so a field nobody declared is caught too."""
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            probe_sections: [Section One]
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert any("forbidden-field" in e and "probe_sections" in e for e in errors), errors

    def test_page_without_scheduling_fields_is_clean(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/some-page.md", """\
            ---
            title: "some page"
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            flashcard_ids: []
            ---

            # some page

            ## Section One

            Content.
        """)
        _write_index(wiki_dir, {})
        errors, _ = lint_wiki(wiki_dir)
        assert [e for e in errors if "forbidden-field" in e] == []


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


# A minimal single-page setup for prose quality tests.
_PROSE_PAGE_TEMPLATE = """\
    ---
    title: "{title}"
    aliases: []
    tags: [git]
    created: 2026-04-09
    updated: 2026-04-09
    source_skill: study-walkthrough
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

    @pytest.mark.parametrize(("body", "label"), [
        ("This is not just a cache, but a durability layer.", "negative-parallelism"),
        ("It is not a lock. It is a hint.", "negative-parallelism"),
        ("The parser normalizes input, ensuring callers see one shape.", "trailing-participle"),
        ("The token is signed, allowing the server to skip a lookup.", "trailing-participle"),
        ("The module serves as the entry point.", "copula-avoidance"),
        ("However, the token expires after an hour.", "conjunctive-opener"),
        ("Studies show that indexes speed up reads.", "vague-attribution"),
    ])
    def test_structural_tell_flagged(self, wiki_dir: Path, body: str, label: str):
        """Documented LLM structural tells → prose-quality warning with that label."""
        _write_page(wiki_dir, "git/tell.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="tell", body=body)
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        hits = [w for w in warnings if "prose-quality" in w and label in w]
        assert len(hits) == 1, f"expected one {label} warning, got: {warnings}"

    @pytest.mark.parametrize("body", [
        "Use a join rather than a subquery.",
        "The migration runs first, leaving the index for later.",
        "Postgres represents each row with a tuple header.",
    ])
    def test_ordinary_prose_not_flagged(self, wiki_dir: Path, body: str):
        """Constructions that are ordinary technical English → no prose-quality warning."""
        _write_page(wiki_dir, "git/ordinary.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="ordinary", body=body)
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        prose = [w for w in warnings if "prose-quality" in w]
        assert prose == [], f"expected no prose-quality warnings, got: {warnings}"

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


class TestHeadingCase:
    def _page(self, wiki_dir: Path, heading: str) -> list[str]:
        _write_page(wiki_dir, "git/heads.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="heads", body=f"## {heading}")
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        return [w for w in warnings if "heading-case" in w]

    @pytest.mark.parametrize("heading", [
        "a heading in sentence case",
        "Mostly Title Case but one lowercase word",
    ])
    def test_sentence_case_heading_flagged(self, wiki_dir: Path, heading: str):
        """Headings not in Title Case → heading-case warning."""
        assert self._page(wiki_dir, heading), f"expected heading-case for {heading!r}"

    @pytest.mark.parametrize("heading", [
        "A Heading in Title Case",
        "not as a Filter",
        "on_delete vs dependent and Which Side Effects Decide",
        "Zone.js: What Triggers CD and What It Cannot Know",
        "Injection Context: Where inject() Is Valid and Where It Throws NG0203",
        "relationships Hold Pointers, included Holds Payloads",
        "What `delegated_type` Expands to",
        "The `_path` Suffix and When It Disappears",
    ])
    def test_conforming_heading_not_flagged(self, wiki_dir: Path, heading: str):
        """Title Case headings, and preserved identifiers, do not warn."""
        assert self._page(wiki_dir, heading) == [], f"unexpected warning for {heading!r}"


class TestProseDensity:
    def _page(self, wiki_dir: Path, sentence: str, times: int) -> list[str]:
        _write_page(wiki_dir, "git/density.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="density", body=" ".join([sentence] * times))
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        return warnings

    def test_high_hedge_rate_flagged(self, wiki_dir: Path):
        """Modals and qualifiers far above the corpus rate → hedge-density warning."""
        warnings = self._page(wiki_dir, "The parser can often skip the lookup.", 12)
        assert any("hedge-density" in w for w in warnings), f"expected hedge-density: {warnings}"

    def test_terse_prose_not_flagged(self, wiki_dir: Path):
        """Short declarative sentences with no hedges → no density warnings."""
        warnings = self._page(wiki_dir, "The parser skips the lookup entirely.", 12)
        assert not any("hedge-density" in w or "sentence-uniformity" in w for w in warnings)

    def _bullet_page(self, wiki_dir: Path, bullets: int) -> list[str]:
        lines = ["The parser walks each row."] + [
            "- The parser reads the header and writes the row into the audit table."
        ] * bullets
        body = "\n".join(lines[:1] + ["    " + ln for ln in lines[1:]])
        _write_page(wiki_dir, "git/bullets.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="bullets", body=body)
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        return warnings

    def test_bullet_dominated_page_flagged(self, wiki_dir: Path):
        """Most of a long page's words sitting in list items → bullet-dominance warning."""
        warnings = self._bullet_page(wiki_dir, 40)
        assert any("bullet-dominance" in w for w in warnings), f"expected dominance: {warnings}"

    def test_short_bullet_page_not_flagged(self, wiki_dir: Path):
        """Same shape below the word floor → no warning; the share is not resolvable."""
        warnings = self._bullet_page(wiki_dir, 5)
        assert not any("bullet-dominance" in w for w in warnings), f"too short to act: {warnings}"

    def test_few_hedges_not_flagged_despite_high_rate(self, wiki_dir: Path):
        """Short page whose rate clears the threshold on only 5 hedges → no warning.

        One hedge word moves the rate by several points on a page this short, so the
        rate is not resolvable enough to act on until enough hedges accumulate.
        """
        hedged = "The parser can skip the lookup for cached rows."
        clean = "The parser reads the header and writes the row."
        _write_page(wiki_dir, "git/few.md", textwrap.dedent(
            _PROSE_PAGE_TEMPLATE.format(title="few", body=" ".join([hedged] * 5 + [clean] * 6))
        ))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        assert not any("hedge-density" in w for w in warnings), f"5 hedges is noise: {warnings}"

    def test_negated_can_not_counted_as_hedge(self, wiki_dir: Path):
        """"can't" states a definite limit, so it is not a hedge."""
        warnings = self._page(wiki_dir, "The site can't tell where the request came from.", 12)
        assert not any("hedge-density" in w for w in warnings), f"can't is not a hedge: {warnings}"

    def test_uniform_mid_length_sentences_flagged(self, wiki_dir: Path):
        """Long sentences all the same length → sentence-uniformity warning."""
        long_sentence = "The request handler reads the header and then writes a fresh row into the audit table."
        warnings = self._page(wiki_dir, long_sentence, 10)
        assert any("sentence-uniformity" in w for w in warnings), f"expected uniformity: {warnings}"

    def test_short_page_low_signal_skipped(self, wiki_dir: Path):
        """Too few words or sentences to be a signal → no density warnings."""
        warnings = self._page(wiki_dir, "The parser can often skip the lookup.", 3)
        assert not any("hedge-density" in w or "sentence-uniformity" in w for w in warnings)


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
---

# wikilink colon

## Section One

[[git/git-restore]]: restores working tree files without touching the index.
""")
        _write_index(wiki_dir, {"git/git-restore": {"file": "git/git-restore.md", "title": "git restore", "aliases": [], "sections": [], "tags": [], "flashcard_ids": [], "created": "2026-04-09", "updated": "2026-04-09"}})
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


def _miscased_page(lint_ignore: list[str] | None = None) -> str:
    """Build a content page whose heading is not in Title Case, so it draws a `heading-case` warning."""
    ignore_block = ""
    if lint_ignore is not None:
        rules = "\n".join(f"    - {r}" for r in lint_ignore)
        ignore_block = f"lint_ignore:\n{rules}\n"
    return (
        "---\n"
        'title: "miscased page"\n'
        "aliases: [miscased alias]\n"
        "tags: [git]\n"
        "created: 2026-04-09\n"
        "updated: 2026-04-09\n"
        "source_skill: study-walkthrough\n"
        "flashcard_ids: []\n"
        f"{ignore_block}"
        "---\n\n"
        "# miscased page\n\n"
        "## a heading in sentence case\n\n"
        "Content.\n"
    )


def _case_warnings(warnings: list[str]) -> list[str]:
    return [w for w in warnings if w.startswith("heading-case:") and "miscased-page.md" in w]


class TestLintIgnore:
    def test_ignore_suppresses_when_clean(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/other-page.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/miscased-page.md", _miscased_page(lint_ignore=["heading-case"]))
        _write_index(wiki_dir, {})
        # Clean working tree (nothing dirty) → suppression active.
        _, warnings = lint_wiki(wiki_dir, dirty_pages=set())
        assert _case_warnings(warnings) == [], warnings

    def test_ignore_inactive_when_dirty(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/other-page.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/miscased-page.md", _miscased_page(lint_ignore=["heading-case"]))
        _write_index(wiki_dir, {})
        # Page has uncommitted changes → ignore does not apply, warning fires.
        _, warnings = lint_wiki(wiki_dir, dirty_pages={"git/miscased-page.md"})
        assert _case_warnings(warnings) != [], warnings

    def test_ignore_wrong_rule_does_not_suppress(self, wiki_dir: Path):
        _write_page(wiki_dir, "git/other-page.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/miscased-page.md", _miscased_page(lint_ignore=["prose-quality"]))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir, dirty_pages=set())
        assert _case_warnings(warnings) != [], warnings

    def test_ignore_default_path_clean_outside_repo(self, wiki_dir: Path):
        # No dirty_pages passed: the git probe runs and finds no repo here,
        # so it reports nothing dirty and the suppression applies.
        _write_page(wiki_dir, "git/other-page.md", MINIMAL_PAGE)
        _write_page(wiki_dir, "git/miscased-page.md", _miscased_page(lint_ignore=["heading-case"]))
        _write_index(wiki_dir, {})
        _, warnings = lint_wiki(wiki_dir)
        assert _case_warnings(warnings) == [], warnings
