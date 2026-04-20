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
