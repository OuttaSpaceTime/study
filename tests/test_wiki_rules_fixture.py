"""The wiki parsing rules both readers implement, pinned by one fixture.

`tests/fixtures/wiki-rules.json` is also run by the wiki-viewer
(`wiki-viewer/tests/wiki-rules-fixture.test.ts`). Each reader keeps its own
implementation; the fixture is what makes them agree.
"""

import json
from pathlib import Path

import pytest

from scripts.wiki.frontmatter import extract_h2s, slugify
from scripts.wiki.links import link_targets

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "wiki-rules.json").read_text())


@pytest.mark.parametrize("case", FIXTURE["link_targets"], ids=lambda c: c["name"])
def test_link_targets(case):
    assert link_targets(case["markdown"]) == case["expected"]


@pytest.mark.parametrize(
    "case", FIXTURE["link_targets_known_gaps"]["cases"], ids=lambda c: c["name"]
)
def test_link_targets_known_gaps_stay_as_documented(case):
    assert link_targets(case["markdown"]) == case["current"]


@pytest.mark.parametrize("case", FIXTURE["h2"], ids=lambda c: c["name"])
def test_extract_h2s(case):
    assert extract_h2s(case["markdown"]) == case["expected"]


@pytest.mark.parametrize("case", FIXTURE["slugify"]["cases"], ids=lambda c: c["name"])
def test_slugify(case):
    assert slugify(case["input"]) == case["expected"]
