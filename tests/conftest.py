"""Shared fixtures for wiki tests."""

import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def wiki_dir(tmp_path: Path) -> Path:
    """Create a temporary wiki directory with an empty index."""
    wd = tmp_path / "wiki"
    wd.mkdir()
    (wd / ".wiki-index.json").write_text("{}\n")
    return wd


@pytest.fixture
def sample_page(wiki_dir: Path) -> Path:
    """Write a sample wiki page and return its path."""
    page_dir = wiki_dir / "git"
    page_dir.mkdir()
    page = page_dir / "test-page.md"
    page.write_text(textwrap.dedent("""\
        ---
        title: "test page"
        aliases: [test alias, another alias]
        tags: [git, testing]
        created: 2026-04-09
        updated: 2026-04-09
        source_skill: study-walkthrough
        flashcard_ids: [cmne7xz9202lx0msonsbfhp3j, cmne7xz1y02k30msouw64srcz, cmne7xyv602if0msoa0ryw0o7]
        next_review: 2026-04-12
        review_interval: 3
        probe_sections: [Section One, Section Two]
        last_probed: [Section One, Section Two]
        ---

        # test page

        ## Section One

        Content here.

        ## Section Two

        More content.
    """))
    return page
