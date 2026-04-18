"""Tests for scripts.wiki.backfill_probes — backfilling probe_sections into existing pages."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from scripts.wiki.backfill_probes import backfill_page, backfill_wiki, eligible_h2s
from scripts.wiki.frontmatter import parse_frontmatter


def _write_page(wiki_dir: Path, rel: str, content: str) -> Path:
    page = wiki_dir / rel
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(textwrap.dedent(content))
    return page


SRS_PAGE = """\
    ---
    title: "test page"
    aliases: []
    tags: [git]
    created: 2026-04-09
    updated: 2026-04-09
    source_skill: study-walkthrough
    next_review: 2026-05-01
    review_interval: 3
    ---

    # test page

    ## Core Concept

    Content.

    ## Gotchas

    Content.

    ## Related Concepts

    - [[other/page]]

    ## References

    - Link.
"""


class TestEligibleH2s:
    def test_excludes_related_concepts(self):
        body = "\n## Core Concept\n\n## Gotchas\n\n## Related Concepts\n\n## References\n"
        assert eligible_h2s(body) == ["Core Concept", "Gotchas"]

    def test_excluded_names_case_insensitive(self):
        body = "\n## TL;DR\n\n## See Also\n\n## Real\n"
        assert eligible_h2s(body) == ["Real"]


class TestBackfillPage:
    def test_adds_probe_sections_when_missing(self, wiki_dir: Path):
        page = _write_page(wiki_dir, "git/a.md", SRS_PAGE)
        result = backfill_page(page, dry_run=False)
        assert result["status"] == "added"
        assert result["probe_sections"] == ["Core Concept", "Gotchas"]
        meta, _ = parse_frontmatter(page.read_text())
        assert meta["probe_sections"] == ["Core Concept", "Gotchas"]
        assert meta["last_probed"] == ["Core Concept", "Gotchas"]

    def test_skips_when_already_present(self, wiki_dir: Path):
        page = _write_page(wiki_dir, "git/a.md", """\
            ---
            title: test
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            next_review: 2026-05-01
            review_interval: 3
            probe_sections: ["Core Concept"]
            last_probed: ["Core Concept"]
            ---

            ## Core Concept

            ## Gotchas
        """)
        original = page.read_text()
        result = backfill_page(page, dry_run=False)
        assert result["status"] == "skipped"
        assert page.read_text() == original

    def test_dry_run_does_not_write(self, wiki_dir: Path):
        page = _write_page(wiki_dir, "git/a.md", SRS_PAGE)
        original = page.read_text()
        result = backfill_page(page, dry_run=True)
        assert result["status"] == "would-add"
        assert page.read_text() == original

    def test_backfills_page_without_next_review(self, wiki_dir: Path):
        """All wiki pages require probe_sections, not just SRS-tracked ones."""
        page = _write_page(wiki_dir, "git/a.md", """\
            ---
            title: test
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            ## Core Concept
        """)
        result = backfill_page(page, dry_run=False)
        assert result["status"] == "added"
        assert result["probe_sections"] == ["Core Concept"]

    def test_warns_when_no_eligible_h2s(self, wiki_dir: Path):
        """Page with only excluded H2s cannot be backfilled automatically."""
        page = _write_page(wiki_dir, "git/a.md", """\
            ---
            title: test
            aliases: []
            tags: [git]
            created: 2026-04-09
            updated: 2026-04-09
            source_skill: study-walkthrough
            ---

            ## Related Concepts

            ## References
        """)
        original = page.read_text()
        result = backfill_page(page, dry_run=False)
        assert result["status"] == "no-eligible-h2s"
        assert page.read_text() == original


class TestBackfillWikiSyncsIndex:
    """backfill_wiki must update .wiki-index.json so the probe-index-drift lint
    rule does not fire for every backfilled page."""

    def test_index_gets_probe_sections_for_backfilled_pages(self, wiki_dir: Path):
        # Seed index with an existing entry that lacks probe_sections (pre-feature state).
        index_path = wiki_dir / ".wiki-index.json"
        index_path.write_text(json.dumps({
            "git/a": {
                "file": "git/a.md",
                "title": "test page",
                "aliases": [],
                "tags": ["git"],
                "sections": ["Core Concept", "Gotchas"],
                "flashcard_ids": [],
                "probe_sections": [],
                "last_probed": [],
                "created": "2026-04-09",
                "updated": "2026-04-09",
            }
        }))
        _write_page(wiki_dir, "git/a.md", SRS_PAGE)

        results = backfill_wiki(wiki_dir, dry_run=False)
        assert any(r["status"] == "added" for r in results)

        index = json.loads(index_path.read_text())
        assert index["git/a"]["probe_sections"] == ["Core Concept", "Gotchas"]
        assert index["git/a"]["last_probed"] == ["Core Concept", "Gotchas"]

    def test_dry_run_does_not_update_index(self, wiki_dir: Path):
        index_path = wiki_dir / ".wiki-index.json"
        original_index = {"git/a": {
            "file": "git/a.md",
            "title": "test page",
            "aliases": [],
            "tags": ["git"],
            "sections": [],
            "flashcard_ids": [],
            "probe_sections": [],
            "last_probed": [],
            "created": "2026-04-09",
            "updated": "2026-04-09",
        }}
        index_path.write_text(json.dumps(original_index))
        _write_page(wiki_dir, "git/a.md", SRS_PAGE)

        backfill_wiki(wiki_dir, dry_run=True)
        assert json.loads(index_path.read_text()) == original_index
