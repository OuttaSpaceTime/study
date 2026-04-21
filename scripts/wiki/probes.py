"""List probes linked to a wiki page (or all probes grouped by wiki page).

Derives the wiki→probe link from each probe's frontmatter `wiki:` field, so
wiki pages stay clean and the link is always fresh.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter


def scan_probes(probes_dir: Path) -> list[dict]:
    """Return one dict per probe file found under probes_dir.

    Skips README.md, _template.md, and any file whose frontmatter does not
    parse or has no body.
    """
    if not probes_dir.is_dir():
        return []

    results: list[dict] = []
    for path in sorted(probes_dir.rglob("*.md")):
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

        results.append(
            {
                "path": str(path),
                "topic": meta.get("topic"),
                "wiki": meta.get("wiki"),
                "session": meta.get("session"),
                "created": meta.get("created"),
            }
        )

    return results


def group_by_wiki(probes: list[dict]) -> dict[str, list[dict]]:
    """Bucket probes by their `wiki:` frontmatter field (empty-string bucket for probes with no wiki link)."""
    out: dict[str, list[dict]] = {}
    for p in probes:
        key = p.get("wiki") or ""
        out.setdefault(key, []).append(p)
    return out


def for_wiki(probes: list[dict], wiki_path: str) -> list[dict]:
    """Return probes whose `wiki:` field matches `wiki_path` exactly."""
    return [p for p in probes if (p.get("wiki") or "") == wiki_path]


def for_topic(probes: list[dict], topic: str) -> list[dict]:
    """Return probes whose `topic:` field matches `topic` exactly."""
    return [p for p in probes if (p.get("topic") or "") == topic]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List probes linked to a wiki page (via probe frontmatter)."
    )
    parser.add_argument(
        "wiki_path",
        nargs="?",
        help="Wiki path (e.g. architecture/event-sourcing). Omit to list all grouped by wiki page.",
    )
    parser.add_argument(
        "--topic",
        help="Alternative lookup: match by probe `topic:` field instead of `wiki:`.",
    )
    parser.add_argument("--count", action="store_true", help="Print count only.")
    parser.add_argument("--probes-dir", default="probes", help="Probes directory.")
    args = parser.parse_args()

    probes = scan_probes(Path(args.probes_dir))

    if args.topic:
        matches = for_topic(probes, args.topic)
    elif args.wiki_path:
        matches = for_wiki(probes, args.wiki_path)
    else:
        matches = None  # signal "all grouped"

    if args.count:
        count = len(matches) if matches is not None else len(probes)
        print(count)
        return

    if matches is None:
        print(json.dumps(group_by_wiki(probes), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(matches, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
