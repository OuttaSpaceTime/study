"""List code challenges linked to wiki pages (or all, grouped by wiki page).

Derives the wiki→challenge link from each challenge's frontmatter `wiki:` and
`section:` fields, so wiki pages stay clean and the link is always fresh.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.wiki.frontmatter import normalize_heading, parse_frontmatter


def scan_challenges(challenges_dir: Path) -> list[dict]:
    """Return one dict per challenge file found under challenges_dir.

    Skips README.md, _template.md, `_`-prefixed files, anything under
    `.attempts/` or `envs/`, and files whose frontmatter does not parse.
    """
    if not challenges_dir.is_dir():
        return []

    results: list[dict] = []
    for path in sorted(challenges_dir.rglob("*.md")):
        rel = path.relative_to(challenges_dir)
        if {".attempts", "envs"} & set(rel.parts[:-1]):
            continue
        name = path.name
        if name in ("README.md", "_template.md"):
            continue
        if name.startswith("_"):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        meta, _body = parse_frontmatter(content)
        if not meta:
            continue

        questions = meta.get("questions")
        results.append(
            {
                "id": str(rel.with_suffix("")),
                "path": str(path),
                "wiki": meta.get("wiki"),
                "section": meta.get("section"),
                "kind": meta.get("kind"),
                "env": meta.get("env"),
                "questions": questions if isinstance(questions, list) else [],
                "created": meta.get("created"),
                "scratch": rel.parts[0] == "scratch",
            }
        )

    return results


def group_by_wiki(challenges: list[dict]) -> dict[str, list[dict]]:
    """Bucket challenges by their `wiki:` field (empty-string bucket for scratch/unlinked)."""
    out: dict[str, list[dict]] = {}
    for c in challenges:
        key = c.get("wiki") or ""
        out.setdefault(key, []).append(c)
    return out


def for_wiki(challenges: list[dict], wiki_key: str) -> list[dict]:
    """Return challenges whose `wiki:` field matches `wiki_key` exactly."""
    return [c for c in challenges if (c.get("wiki") or "") == wiki_key]


def for_section(challenges: list[dict], wiki_key: str, section: str) -> list[dict]:
    """Return challenges for `wiki_key` whose `section:` normalize-matches `section`."""
    target = normalize_heading(section)
    return [
        c
        for c in for_wiki(challenges, wiki_key)
        if c.get("section") and normalize_heading(str(c["section"])) == target
    ]


def scratch(challenges: list[dict]) -> list[dict]:
    """Return scratch challenges (files under challenges/scratch/)."""
    return [c for c in challenges if c.get("scratch")]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List code challenges linked to a wiki page (via challenge frontmatter)."
    )
    parser.add_argument(
        "wiki_key",
        nargs="?",
        help="Wiki key (e.g. security/hsts). Omit to list all grouped by wiki page.",
    )
    parser.add_argument(
        "--section",
        help="Filter to the challenge for one H2 section (normalized match; requires wiki_key).",
    )
    parser.add_argument("--scratch", action="store_true", help="List scratch challenges only.")
    parser.add_argument("--count", action="store_true", help="Print count only.")
    parser.add_argument("--challenges-dir", default="challenges", help="Challenges directory.")
    args = parser.parse_args()

    challenges = scan_challenges(Path(args.challenges_dir))

    if args.scratch:
        matches = scratch(challenges)
    elif args.wiki_key and args.section:
        matches = for_section(challenges, args.wiki_key, args.section)
    elif args.wiki_key:
        matches = for_wiki(challenges, args.wiki_key)
    else:
        matches = None  # signal "all grouped"

    if args.count:
        count = len(matches) if matches is not None else len(challenges)
        print(count)
        return

    if matches is None:
        print(json.dumps(group_by_wiki(challenges), indent=2, ensure_ascii=False, default=str))
    else:
        print(json.dumps(matches, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
