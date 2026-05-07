"""Tests for MOC auto-linking (scripts.wiki.write.update_moc) and lint coverage."""

import textwrap
from pathlib import Path

from scripts.wiki.lint import lint_wiki
from scripts.wiki.write import update_moc


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


MOC_TEMPLATE = """\
    ---
    title: "Git Index"
    aliases: [git-moc]
    tags: [moc, git]
    category: work
    created: 2026-04-20
    updated: 2026-04-20
    source_skill: manual
    probe_sections: [Pages]
    last_probed: [Pages]
    allow_orphan: true
    ---

    # Git Index

    Map of content for the `git/` folder.

    ## Pages

{pages}
"""


PAGE_TEMPLATE = """\
    ---
    title: "{title}"
    aliases: [{slug}-alias]
    tags: [git]
    category: work
    created: 2026-04-20
    updated: 2026-04-20
    source_skill: study-walkthrough
    probe_sections: [Overview]
    last_probed: [Overview]
    ---

    # {title}

    ## Overview

    Content.
"""


def _moc(wiki_dir: Path, folder: str, pages: list[str]) -> Path:
    body = "\n".join(f"    - [[{folder}/{s}]]" for s in pages) or "    "
    return _write(
        wiki_dir / folder / f"{folder}-index.md",
        MOC_TEMPLATE.format(pages=body),
    )


def _page(wiki_dir: Path, folder: str, slug: str, title: str | None = None) -> Path:
    return _write(
        wiki_dir / folder / f"{slug}.md",
        PAGE_TEMPLATE.format(slug=slug, title=title or slug),
    )


class TestUpdateMoc:
    def test_adds_new_page_to_moc(self, wiki_dir: Path):
        _moc(wiki_dir, "git", [])
        page = _page(wiki_dir, "git", "git-restore", "git restore")
        update_moc(page, wiki_dir)
        moc_text = (wiki_dir / "git" / "git-index.md").read_text()
        assert "[[git/git-restore]]" in moc_text

    def test_sorted_alphabetically(self, wiki_dir: Path):
        _moc(wiki_dir, "git", [])
        _page(wiki_dir, "git", "zulu")
        _page(wiki_dir, "git", "alpha")
        _page(wiki_dir, "git", "mike")
        update_moc(wiki_dir / "git" / "alpha.md", wiki_dir)
        moc_text = (wiki_dir / "git" / "git-index.md").read_text()
        alpha_i = moc_text.index("[[git/alpha]]")
        mike_i = moc_text.index("[[git/mike]]")
        zulu_i = moc_text.index("[[git/zulu]]")
        assert alpha_i < mike_i < zulu_i

    def test_excludes_moc_itself(self, wiki_dir: Path):
        _moc(wiki_dir, "git", [])
        _page(wiki_dir, "git", "git-restore")
        update_moc(wiki_dir / "git" / "git-restore.md", wiki_dir)
        moc_text = (wiki_dir / "git" / "git-index.md").read_text()
        assert "[[git/git-index]]" not in moc_text

    def test_moc_write_rebuilds_own_list(self, wiki_dir: Path):
        moc = _moc(wiki_dir, "git", [])
        _page(wiki_dir, "git", "git-restore")
        update_moc(moc, wiki_dir)
        assert "[[git/git-restore]]" in moc.read_text()

    def test_no_moc_does_not_error(self, wiki_dir: Path):
        page = _page(wiki_dir, "git", "git-restore")
        update_moc(page, wiki_dir)

    def test_rebuild_drops_deleted_pages(self, wiki_dir: Path):
        _moc(wiki_dir, "git", ["git-restore", "git-ghost"])
        _page(wiki_dir, "git", "git-restore")
        update_moc(wiki_dir / "git" / "git-restore.md", wiki_dir)
        moc_text = (wiki_dir / "git" / "git-index.md").read_text()
        assert "[[git/git-ghost]]" not in moc_text
        assert "[[git/git-restore]]" in moc_text

    def test_preserves_other_sections(self, wiki_dir: Path):
        moc_path = wiki_dir / "git" / "git-index.md"
        moc_path.parent.mkdir(parents=True, exist_ok=True)
        moc_path.write_text(textwrap.dedent("""\
            ---
            title: "Git Index"
            aliases: [git-moc]
            tags: [moc, git]
            category: work
            created: 2026-04-20
            updated: 2026-04-20
            source_skill: manual
            probe_sections: [Pages]
            last_probed: [Pages]
            allow_orphan: true
            ---

            # Git Index

            Intro paragraph that must survive.

            ## Pages

            - stale content

            ## Notes

            Footer section that must also survive.
        """))
        _page(wiki_dir, "git", "git-restore")
        update_moc(wiki_dir / "git" / "git-restore.md", wiki_dir)
        text = moc_path.read_text()
        assert "Intro paragraph that must survive." in text
        assert "Footer section that must also survive." in text
        assert "stale content" not in text
        assert "[[git/git-restore]]" in text


SUB_MOC_TEMPLATE = """\
    ---
    title: "Routing Index"
    aliases: [routing-moc]
    tags: [moc, routing]
    created: 2026-04-20
    updated: 2026-04-20
    source_skill: manual
    flashcard_ids: []
    probe_sections: [Pages]
    last_probed: [Pages]
    ---

    # Routing Index

    ## Pages

{pages}
"""


SUB_PAGE_TEMPLATE = """\
    ---
    title: "{title}"
    aliases: [{slug}-alias]
    tags: [rails, routing]
    created: 2026-04-20
    updated: 2026-04-20
    source_skill: study-walkthrough
    probe_sections: [Overview]
    last_probed: [Overview]
    ---

    # {title}

    ## Overview

    Content.
"""


def _sub_moc(wiki_dir: Path, top: str, sub: str, pages: list[str]) -> Path:
    body = "\n".join(f"    - [[{top}/{sub}/{s}]]" for s in pages) or "    "
    return _write(
        wiki_dir / top / sub / f"{sub}-index.md",
        SUB_MOC_TEMPLATE.format(pages=body),
    )


def _sub_page(wiki_dir: Path, top: str, sub: str, slug: str, title: str | None = None) -> Path:
    return _write(
        wiki_dir / top / sub / f"{slug}.md",
        SUB_PAGE_TEMPLATE.format(slug=slug, title=title or slug),
    )


class TestSubMocUpdate:
    def test_sub_moc_lists_its_children(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", [])
        _sub_moc(wiki_dir, "rails", "routing", [])
        page = _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        update_moc(page, wiki_dir)
        sub_text = (wiki_dir / "rails" / "routing" / "routing-index.md").read_text()
        assert "[[rails/routing/shallow-routing]]" in sub_text

    def test_first_sub_page_write_triggers_parent_rebuild(self, wiki_dir: Path):
        """Writing the first page in a brand-new sub-folder must update the parent MOC."""
        _moc(wiki_dir, "rails", [])
        _sub_moc(wiki_dir, "rails", "routing", [])
        page = _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        update_moc(page, wiki_dir)
        parent_text = (wiki_dir / "rails" / "rails-index.md").read_text()
        assert "[[rails/routing/routing-index]]" in parent_text

    def test_parent_lists_sub_mocs_then_loose_pages(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", [])
        _sub_moc(wiki_dir, "rails", "routing", [])
        _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        loose = _page(wiki_dir, "rails", "activerecord-pick")
        update_moc(loose, wiki_dir)
        parent_text = (wiki_dir / "rails" / "rails-index.md").read_text()
        sub_i = parent_text.index("[[rails/routing/routing-index]]")
        loose_i = parent_text.index("[[rails/activerecord-pick]]")
        assert sub_i < loose_i

    def test_pages_in_subfolder_not_listed_in_parent(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", [])
        _sub_moc(wiki_dir, "rails", "routing", [])
        page = _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        update_moc(page, wiki_dir)
        parent_text = (wiki_dir / "rails" / "rails-index.md").read_text()
        assert "[[rails/shallow-routing]]" not in parent_text


class TestSubMocLint:
    def _wiki_with_subfolder(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", ["routing/routing-index"])
        _sub_moc(wiki_dir, "rails", "routing", ["shallow-routing"])
        _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        (wiki_dir / ".wiki-index.json").write_text("{}\n")

    def test_sub_page_drift_against_parent_not_flagged(self, wiki_dir: Path):
        """A page in rails/routing/ should NOT trigger moc-drift against rails-index."""
        self._wiki_with_subfolder(wiki_dir)
        _, warnings = lint_wiki(wiki_dir)
        bad = [w for w in warnings if "moc-drift" in w and "rails-index" in w and "shallow-routing" in w]
        assert bad == [], f"sub-folder page must not drift against parent: {bad}"

    def test_sub_moc_missing_from_parent_flagged(self, wiki_dir: Path):
        """Parent MOC missing the sub-MOC link → moc-drift warning."""
        _moc(wiki_dir, "rails", [])  # no sub-MOC link
        _sub_moc(wiki_dir, "rails", "routing", ["shallow-routing"])
        _sub_page(wiki_dir, "rails", "routing", "shallow-routing")
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert any("moc-drift" in w and "routing-index" in w for w in warnings), warnings

    def test_sub_moc_does_not_require_allow_orphan(self, wiki_dir: Path):
        """Sub-MOCs are linked from parent; lint must not require allow_orphan: true on them."""
        self._wiki_with_subfolder(wiki_dir)
        errors, _ = lint_wiki(wiki_dir)
        assert not any("moc-allow-orphan-missing" in e and "routing-index" in e for e in errors), errors

    def test_sub_moc_still_requires_moc_tag(self, wiki_dir: Path):
        """Sub-MOC missing 'moc' in tags → moc-tag-missing error."""
        _moc(wiki_dir, "rails", ["routing/routing-index"])
        _write(
            wiki_dir / "rails" / "routing" / "routing-index.md",
            textwrap.dedent("""\
                ---
                title: "Routing Index"
                aliases: [routing-moc]
                tags: [routing]
                created: 2026-04-20
                updated: 2026-04-20
                source_skill: manual
                flashcard_ids: []
                probe_sections: [Pages]
                last_probed: [Pages]
                ---

                # Routing Index

                ## Pages
            """),
        )
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        errors, _ = lint_wiki(wiki_dir)
        assert any("moc-tag-missing" in e and "routing-index" in e for e in errors), errors


class TestMocSplitSuggestion:
    def test_suggestion_when_cluster_meets_threshold(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", [])
        # 8 routing-tagged pages → triggers (folder size 8, cluster 8).
        for i in range(8):
            _write(
                wiki_dir / "rails" / f"r{i}.md",
                textwrap.dedent(f"""\
                    ---
                    title: "r{i}"
                    aliases: [r{i}-a]
                    tags: [rails, routing]
                    created: 2026-04-20
                    updated: 2026-04-20
                    source_skill: study-walkthrough
                    probe_sections: [Overview]
                    last_probed: [Overview]
                    ---

                    # r{i}

                    ## Overview

                    .
                """),
            )
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert any("moc-split-suggestion" in w and "routing" in w for w in warnings), warnings

    def test_no_suggestion_below_folder_threshold(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", [])
        # 4 routing-tagged pages but folder has only 4 — fails ≥8 rule.
        for i in range(4):
            _write(
                wiki_dir / "rails" / f"r{i}.md",
                textwrap.dedent(f"""\
                    ---
                    title: "r{i}"
                    aliases: [r{i}-a]
                    tags: [rails, routing]
                    created: 2026-04-20
                    updated: 2026-04-20
                    source_skill: study-walkthrough
                    probe_sections: [Overview]
                    last_probed: [Overview]
                    ---

                    # r{i}

                    ## Overview

                    .
                """),
            )
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert not any("moc-split-suggestion" in w for w in warnings), warnings

    def test_suggestion_suppressed_when_sub_moc_exists(self, wiki_dir: Path):
        _moc(wiki_dir, "rails", ["routing/routing-index"])
        _sub_moc(wiki_dir, "rails", "routing", [])
        # 4 routing pages still in top-level (mid-migration) plus 4 unrelated tags
        for i in range(4):
            _write(
                wiki_dir / "rails" / f"r{i}.md",
                textwrap.dedent(f"""\
                    ---
                    title: "r{i}"
                    aliases: [r{i}-a]
                    tags: [rails, routing]
                    created: 2026-04-20
                    updated: 2026-04-20
                    source_skill: study-walkthrough
                    probe_sections: [Overview]
                    last_probed: [Overview]
                    ---

                    # r{i}

                    ## Overview

                    .
                """),
            )
        for i in range(4):
            _write(
                wiki_dir / "rails" / f"a{i}.md",
                textwrap.dedent(f"""\
                    ---
                    title: "a{i}"
                    aliases: [a{i}-a]
                    tags: [rails]
                    created: 2026-04-20
                    updated: 2026-04-20
                    source_skill: study-walkthrough
                    probe_sections: [Overview]
                    last_probed: [Overview]
                    ---

                    # a{i}

                    ## Overview

                    .
                """),
            )
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert not any(
            "moc-split-suggestion" in w and "routing" in w for w in warnings
        ), warnings


class TestMocCoverageLint:
    def test_moc_drift_warning(self, wiki_dir: Path):
        _moc(wiki_dir, "git", [])
        _page(wiki_dir, "git", "git-restore")
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert any("moc-drift" in w and "git-restore" in w for w in warnings)

    def test_moc_missing_warning(self, wiki_dir: Path):
        _page(wiki_dir, "ruby", "transform-values")
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert any("moc-missing" in w and "ruby" in w for w in warnings)

    def test_clean_when_all_listed(self, wiki_dir: Path):
        _moc(wiki_dir, "git", ["git-restore"])
        _page(wiki_dir, "git", "git-restore")
        (wiki_dir / ".wiki-index.json").write_text("{}\n")
        _, warnings = lint_wiki(wiki_dir)
        assert not any("moc-drift" in w for w in warnings)
        assert not any("moc-missing" in w for w in warnings)
