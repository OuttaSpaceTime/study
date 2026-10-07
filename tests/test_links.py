"""scripts/wiki/links.py: the link rules lint and the Omvida app share."""

from scripts.wiki.frontmatter import extract_h2s
from scripts.wiki.links import link_targets, strip_code


def test_link_targets_skip_code_and_embeds_and_keep_order():
    body = "See [[b/two|Two]] and [[a/one#Part]].\n`[[not/inline]]` ``[[not/double]]``\n```\n[[not/fenced]]\n```\n![[img.png]]"
    assert link_targets(body) == ["b/two", "a/one"]


def test_strip_code_removes_fenced_and_inline():
    assert strip_code("x `y` z\n```\ncode\n```\nw") == "x  z\n\nw"


def test_h2s_inside_fences_are_not_sections():
    body = "## Real\n```bash\n## a shell comment\n```\n##  Spaced  \n### Sub"
    assert extract_h2s(body) == ["Real", "Spaced"]
