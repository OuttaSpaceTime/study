"""Tests for scripts.wiki.probes — scan_probes, for_wiki, for_topic, group_by_wiki."""

import textwrap
from pathlib import Path

import pytest

from scripts.wiki.probes import for_topic, for_wiki, group_by_wiki, scan_probes


def _write_probe(
    dir: Path,
    filename: str,
    *,
    topic: str | None = "event-sourcing",
    wiki: str | None = "architecture/event-sourcing",
    session: str | None = "2026-04-21-walkthrough",
    created: str | None = "2026-04-21 09:15",
) -> Path:
    dir.mkdir(parents=True, exist_ok=True)
    path = dir / filename
    fm_lines = ["---"]
    if topic is not None:
        fm_lines.append(f"topic: {topic}")
    if wiki is not None:
        fm_lines.append(f"wiki: {wiki}")
    if session is not None:
        fm_lines.append(f"session: {session}")
    if created is not None:
        fm_lines.append(f'created: "{created}"')
    fm_lines.append("---")
    fm = "\n".join(fm_lines) + "\n"
    body = textwrap.dedent("""
        ## Prediction
        Expected X.

        ## Command
        ```bash
        echo test
        ```

        ## Output
        ```
        test
        ```

        ## Takeaway
        Confirmed.
    """)
    path.write_text(fm + body)
    return path


@pytest.fixture
def probes_dir(tmp_path: Path) -> Path:
    root = tmp_path / "probes"
    root.mkdir()
    return root


class TestScanProbes:
    def test_missing_directory_returns_empty(self, tmp_path: Path):
        assert scan_probes(tmp_path / "does-not-exist") == []

    def test_empty_directory_returns_empty(self, probes_dir: Path):
        assert scan_probes(probes_dir) == []

    def test_single_probe_parsed(self, probes_dir: Path):
        _write_probe(probes_dir / "event-sourcing", "2026-04-21-0915-replay.md")
        result = scan_probes(probes_dir)
        assert len(result) == 1
        entry = result[0]
        assert entry["topic"] == "event-sourcing"
        assert entry["wiki"] == "architecture/event-sourcing"
        assert entry["session"] == "2026-04-21-walkthrough"
        assert entry["created"] == "2026-04-21 09:15"
        assert entry["path"].endswith("2026-04-21-0915-replay.md")

    def test_readme_skipped(self, probes_dir: Path):
        (probes_dir / "README.md").write_text("---\ntopic: x\n---\nbody")
        assert scan_probes(probes_dir) == []

    def test_template_skipped(self, probes_dir: Path):
        (probes_dir / "_template.md").write_text("---\ntopic: x\n---\nbody")
        assert scan_probes(probes_dir) == []

    def test_underscore_prefixed_skipped(self, probes_dir: Path):
        _write_probe(probes_dir / "event-sourcing", "_draft.md")
        assert scan_probes(probes_dir) == []

    def test_file_without_frontmatter_skipped(self, probes_dir: Path):
        topic_dir = probes_dir / "event-sourcing"
        topic_dir.mkdir()
        (topic_dir / "no-frontmatter.md").write_text("just some body\n")
        assert scan_probes(probes_dir) == []

    def test_multiple_probes_sorted_by_path(self, probes_dir: Path):
        _write_probe(probes_dir / "a-topic", "2026-04-21-0915-one.md", topic="a-topic")
        _write_probe(probes_dir / "a-topic", "2026-04-22-1103-two.md", topic="a-topic")
        _write_probe(probes_dir / "b-topic", "2026-04-21-1000-three.md", topic="b-topic")
        result = scan_probes(probes_dir)
        assert len(result) == 3
        paths = [e["path"] for e in result]
        assert paths == sorted(paths)

    def test_non_md_files_ignored(self, probes_dir: Path):
        topic_dir = probes_dir / "event-sourcing"
        topic_dir.mkdir()
        (topic_dir / "notes.txt").write_text("---\ntopic: x\n---\nbody")
        (topic_dir / "data.json").write_text('{"topic": "x"}')
        assert scan_probes(probes_dir) == []

    def test_missing_optional_fields_are_none(self, probes_dir: Path):
        _write_probe(
            probes_dir / "event-sourcing",
            "2026-04-21-0915-bare.md",
            wiki=None,
            session=None,
            created=None,
        )
        result = scan_probes(probes_dir)
        assert len(result) == 1
        entry = result[0]
        assert entry["topic"] == "event-sourcing"
        assert entry["wiki"] is None
        assert entry["session"] is None
        assert entry["created"] is None


class TestForWiki:
    def test_empty_list(self):
        assert for_wiki([], "architecture/event-sourcing") == []

    def test_exact_match(self):
        probes = [
            {"wiki": "architecture/event-sourcing", "topic": "event-sourcing"},
            {"wiki": "security/hsts", "topic": "hsts"},
        ]
        result = for_wiki(probes, "architecture/event-sourcing")
        assert len(result) == 1
        assert result[0]["topic"] == "event-sourcing"

    def test_no_match_returns_empty(self):
        probes = [{"wiki": "architecture/event-sourcing", "topic": "event-sourcing"}]
        assert for_wiki(probes, "other/page") == []

    def test_probe_with_no_wiki_field_not_matched(self):
        probes = [{"wiki": None, "topic": "x"}]
        assert for_wiki(probes, "any/path") == []


class TestForTopic:
    def test_exact_match(self):
        probes = [
            {"wiki": "architecture/event-sourcing", "topic": "event-sourcing"},
            {"wiki": "architecture/cqrs", "topic": "cqrs"},
        ]
        result = for_topic(probes, "event-sourcing")
        assert len(result) == 1
        assert result[0]["topic"] == "event-sourcing"

    def test_no_match(self):
        probes = [{"wiki": "x", "topic": "a"}]
        assert for_topic(probes, "b") == []


class TestGroupByWiki:
    def test_empty(self):
        assert group_by_wiki([]) == {}

    def test_groups_by_wiki_field(self):
        probes = [
            {"wiki": "architecture/event-sourcing", "topic": "event-sourcing"},
            {"wiki": "architecture/event-sourcing", "topic": "event-sourcing"},
            {"wiki": "security/hsts", "topic": "hsts"},
        ]
        result = group_by_wiki(probes)
        assert set(result.keys()) == {"architecture/event-sourcing", "security/hsts"}
        assert len(result["architecture/event-sourcing"]) == 2
        assert len(result["security/hsts"]) == 1

    def test_missing_wiki_field_bucketed_empty_string(self):
        probes = [
            {"wiki": None, "topic": "orphan"},
            {"wiki": "x", "topic": "a"},
        ]
        result = group_by_wiki(probes)
        assert result[""] == [{"wiki": None, "topic": "orphan"}]
        assert result["x"] == [{"wiki": "x", "topic": "a"}]


class TestIntegration:
    def test_end_to_end_with_real_files(self, probes_dir: Path):
        _write_probe(
            probes_dir / "event-sourcing",
            "2026-04-21-0915-replay.md",
            topic="event-sourcing",
            wiki="architecture/event-sourcing",
        )
        _write_probe(
            probes_dir / "event-sourcing",
            "2026-04-22-1103-upcaster.md",
            topic="event-sourcing",
            wiki="architecture/event-sourcing",
        )
        _write_probe(
            probes_dir / "hsts",
            "2026-04-21-1000-preload.md",
            topic="hsts",
            wiki="security/hsts",
        )
        (probes_dir / "README.md").write_text("readme body")
        (probes_dir / "_template.md").write_text("---\ntopic: tpl\n---\n")

        probes = scan_probes(probes_dir)
        assert len(probes) == 3

        es_probes = for_wiki(probes, "architecture/event-sourcing")
        assert len(es_probes) == 2
        assert {p["path"].split("/")[-1] for p in es_probes} == {
            "2026-04-21-0915-replay.md",
            "2026-04-22-1103-upcaster.md",
        }

        hsts_probes = for_topic(probes, "hsts")
        assert len(hsts_probes) == 1

        grouped = group_by_wiki(probes)
        assert len(grouped["architecture/event-sourcing"]) == 2
        assert len(grouped["security/hsts"]) == 1
