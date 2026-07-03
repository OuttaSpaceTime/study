"""Tests for scripts.wiki.challenges — scan_challenges, for_wiki, for_section, scratch, group_by_wiki."""

import textwrap
from pathlib import Path

import pytest

from scripts.wiki.challenges import (
    for_section,
    for_wiki,
    group_by_wiki,
    scan_challenges,
    scratch,
)


def _write_challenge(
    dir: Path,
    filename: str,
    *,
    wiki: str | None = "security/hsts",
    section: str | None = "Preload",
    kind: str | None = "write-code",
    env: str | None = "node24",
    questions: list[str] | None = None,
    created: str | None = "2026-07-03",
) -> Path:
    dir.mkdir(parents=True, exist_ok=True)
    path = dir / filename
    fm_lines = ["---"]
    if wiki is not None:
        fm_lines.append(f"wiki: {wiki}")
    if section is not None:
        fm_lines.append(f"section: {section}")
    if kind is not None:
        fm_lines.append(f"kind: {kind}")
    if env is not None:
        fm_lines.append(f"env: {env}")
    if questions is None:
        questions = ["Why does this work?"]
    if questions:
        fm_lines.append("questions:")
        for q in questions:
            fm_lines.append(f"- {q}")
    if created is not None:
        fm_lines.append(f"created: {created}")
    fm_lines.append("---")
    fm = "\n".join(fm_lines) + "\n"
    body = textwrap.dedent("""
        ## Brief
        Fill in the blank.

        ## Stub
        ```js
        // TODO
        ```

        ## Solution
        ```js
        console.log("done")
        ```

        ## Expected Output
        ```
        done
        ```
    """)
    path.write_text(fm + body)
    return path


@pytest.fixture
def challenges_dir(tmp_path: Path) -> Path:
    root = tmp_path / "challenges"
    root.mkdir()
    return root


class TestScanChallenges:
    def test_missing_directory_returns_empty(self, tmp_path: Path):
        assert scan_challenges(tmp_path / "does-not-exist") == []

    def test_empty_directory_returns_empty(self, challenges_dir: Path):
        assert scan_challenges(challenges_dir) == []

    def test_single_challenge_parsed(self, challenges_dir: Path):
        _write_challenge(challenges_dir / "security", "hsts-preload.md")
        result = scan_challenges(challenges_dir)
        assert len(result) == 1
        entry = result[0]
        assert entry["id"] == "security/hsts-preload"
        assert entry["wiki"] == "security/hsts"
        assert entry["section"] == "Preload"
        assert entry["kind"] == "write-code"
        assert entry["env"] == "node24"
        assert entry["questions"] == ["Why does this work?"]
        assert entry["created"] == "2026-07-03"
        assert entry["scratch"] is False
        assert entry["path"].endswith("hsts-preload.md")

    def test_scratch_challenge_flagged(self, challenges_dir: Path):
        _write_challenge(
            challenges_dir / "scratch",
            "2026-07-03-1430-closures.md",
            wiki=None,
            section=None,
        )
        result = scan_challenges(challenges_dir)
        assert len(result) == 1
        entry = result[0]
        assert entry["scratch"] is True
        assert entry["id"] == "scratch/2026-07-03-1430-closures"
        assert entry["wiki"] is None
        assert entry["section"] is None

    def test_readme_and_template_skipped(self, challenges_dir: Path):
        (challenges_dir / "README.md").write_text("---\nwiki: x\n---\nbody")
        (challenges_dir / "_template.md").write_text("---\nwiki: x\n---\nbody")
        assert scan_challenges(challenges_dir) == []

    def test_underscore_prefixed_skipped(self, challenges_dir: Path):
        _write_challenge(challenges_dir / "security", "_draft.md")
        assert scan_challenges(challenges_dir) == []

    def test_attempts_dir_skipped(self, challenges_dir: Path):
        _write_challenge(challenges_dir / ".attempts" / "security", "hsts-preload.md")
        assert scan_challenges(challenges_dir) == []

    def test_envs_dir_skipped(self, challenges_dir: Path):
        _write_challenge(challenges_dir / "envs" / "rails-play", "NOTES.md")
        assert scan_challenges(challenges_dir) == []

    def test_file_without_frontmatter_skipped(self, challenges_dir: Path):
        topic_dir = challenges_dir / "security"
        topic_dir.mkdir()
        (topic_dir / "no-frontmatter.md").write_text("just some body\n")
        assert scan_challenges(challenges_dir) == []

    def test_non_md_files_ignored(self, challenges_dir: Path):
        (challenges_dir / "envs.json").write_text('{"node24": {"type": "inline"}}')
        topic_dir = challenges_dir / "security"
        topic_dir.mkdir()
        (topic_dir / "notes.txt").write_text("---\nwiki: x\n---\nbody")
        assert scan_challenges(challenges_dir) == []

    def test_multiple_challenges_sorted_by_path(self, challenges_dir: Path):
        _write_challenge(challenges_dir / "a-topic", "one.md")
        _write_challenge(challenges_dir / "a-topic", "two.md")
        _write_challenge(challenges_dir / "b-topic", "three.md")
        result = scan_challenges(challenges_dir)
        assert len(result) == 3
        paths = [e["path"] for e in result]
        assert paths == sorted(paths)

    def test_missing_optional_fields_are_none_or_empty(self, challenges_dir: Path):
        _write_challenge(
            challenges_dir / "security",
            "bare.md",
            wiki=None,
            section=None,
            env=None,
            questions=[],
            created=None,
        )
        result = scan_challenges(challenges_dir)
        assert len(result) == 1
        entry = result[0]
        assert entry["wiki"] is None
        assert entry["section"] is None
        assert entry["kind"] == "write-code"
        assert entry["env"] is None
        assert entry["questions"] == []
        assert entry["created"] is None


class TestForWiki:
    def test_empty_list(self):
        assert for_wiki([], "security/hsts") == []

    def test_exact_match(self):
        challenges = [
            {"wiki": "security/hsts", "id": "security/hsts-preload"},
            {"wiki": "git/rebase", "id": "git/rebase-onto"},
        ]
        result = for_wiki(challenges, "security/hsts")
        assert len(result) == 1
        assert result[0]["id"] == "security/hsts-preload"

    def test_no_match_returns_empty(self):
        challenges = [{"wiki": "security/hsts", "id": "security/hsts-preload"}]
        assert for_wiki(challenges, "other/page") == []

    def test_challenge_with_no_wiki_field_not_matched(self):
        challenges = [{"wiki": None, "id": "scratch/x"}]
        assert for_wiki(challenges, "any/path") == []


class TestForSection:
    def test_exact_match(self):
        challenges = [
            {"wiki": "security/hsts", "section": "Preload", "id": "a"},
            {"wiki": "security/hsts", "section": "Browser Storage", "id": "b"},
        ]
        result = for_section(challenges, "security/hsts", "Preload")
        assert len(result) == 1
        assert result[0]["id"] == "a"

    def test_normalized_match_case_and_trailing_punctuation(self):
        challenges = [{"wiki": "security/hsts", "section": "The Preload List:", "id": "a"}]
        result = for_section(challenges, "security/hsts", "the preload list")
        assert len(result) == 1

    def test_wrong_wiki_not_matched(self):
        challenges = [{"wiki": "security/hsts", "section": "Preload", "id": "a"}]
        assert for_section(challenges, "git/rebase", "Preload") == []

    def test_no_match(self):
        challenges = [{"wiki": "security/hsts", "section": "Preload", "id": "a"}]
        assert for_section(challenges, "security/hsts", "Browser Storage") == []

    def test_missing_section_field_not_matched(self):
        challenges = [{"wiki": "security/hsts", "section": None, "id": "a"}]
        assert for_section(challenges, "security/hsts", "Preload") == []


class TestScratch:
    def test_filters_scratch_only(self):
        challenges = [
            {"id": "scratch/x", "scratch": True},
            {"id": "security/y", "scratch": False},
        ]
        result = scratch(challenges)
        assert len(result) == 1
        assert result[0]["id"] == "scratch/x"

    def test_empty(self):
        assert scratch([]) == []


class TestGroupByWiki:
    def test_empty(self):
        assert group_by_wiki([]) == {}

    def test_groups_by_wiki_field(self):
        challenges = [
            {"wiki": "security/hsts", "id": "a"},
            {"wiki": "security/hsts", "id": "b"},
            {"wiki": "git/rebase", "id": "c"},
        ]
        result = group_by_wiki(challenges)
        assert set(result.keys()) == {"security/hsts", "git/rebase"}
        assert len(result["security/hsts"]) == 2
        assert len(result["git/rebase"]) == 1

    def test_missing_wiki_field_bucketed_empty_string(self):
        challenges = [
            {"wiki": None, "id": "scratch/x"},
            {"wiki": "git/rebase", "id": "c"},
        ]
        result = group_by_wiki(challenges)
        assert result[""] == [{"wiki": None, "id": "scratch/x"}]


class TestIntegration:
    def test_end_to_end_with_real_files(self, challenges_dir: Path):
        _write_challenge(challenges_dir / "security", "hsts-preload.md")
        _write_challenge(
            challenges_dir / "security",
            "hsts-header.md",
            section="Browser Storage",
        )
        _write_challenge(
            challenges_dir / "git",
            "rebase-onto.md",
            wiki="git/rebase",
            section="Moving Commits",
            env="ruby",
        )
        _write_challenge(
            challenges_dir / "scratch",
            "2026-07-03-1430-closures.md",
            wiki=None,
            section=None,
        )
        (challenges_dir / "README.md").write_text("readme body")
        (challenges_dir / "_template.md").write_text("---\nwiki: tpl\n---\n")
        (challenges_dir / "envs.json").write_text('{"node24": {"type": "inline"}}')

        challenges = scan_challenges(challenges_dir)
        assert len(challenges) == 4

        hsts = for_wiki(challenges, "security/hsts")
        assert {c["id"] for c in hsts} == {"security/hsts-preload", "security/hsts-header"}

        preload = for_section(challenges, "security/hsts", "preload")
        assert len(preload) == 1
        assert preload[0]["id"] == "security/hsts-preload"

        assert len(scratch(challenges)) == 1

        grouped = group_by_wiki(challenges)
        assert len(grouped["security/hsts"]) == 2
        assert len(grouped[""]) == 1
