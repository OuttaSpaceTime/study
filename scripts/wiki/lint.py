"""Wiki linter — checks link integrity, frontmatter, absolute paths, orphans, alias collisions."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter, slugify
from scripts.wiki.index import load_index

REQUIRED_FIELDS = {"title", "created", "tags"}


def lint_wiki(wiki_dir: Path) -> list[str]:
    """Run all lint checks. Returns list of error strings (empty = clean)."""
    wiki_dir = Path(wiki_dir)
    md_files = sorted(
        p
        for p in wiki_dir.rglob("*.md")
        if ".obsidian" not in p.parts
    )

    if not md_files:
        return []

    index_path = wiki_dir / ".wiki-index.json"
    index = load_index(index_path)

    errors: list[str] = []
    errors.extend(_check_frontmatter(wiki_dir, md_files))
    link_errors, inbound = _check_wikilinks(wiki_dir, md_files)
    errors.extend(link_errors)
    errors.extend(_check_orphans(wiki_dir, md_files, inbound))
    errors.extend(_check_alias_collisions(index))
    errors.extend(_check_slugs(wiki_dir, md_files))
    errors.extend(_check_flashcard_ids(wiki_dir, index))
    return errors


def _check_frontmatter(wiki_dir: Path, md_files: list[Path]) -> list[str]:
    errors = []
    for f in md_files:
        rel = str(f.relative_to(wiki_dir))
        content = f.read_text()
        if not content.startswith("---\n"):
            errors.append(f"missing-frontmatter: {rel} has no YAML frontmatter")
            continue
        meta, _ = parse_frontmatter(content)
        for field in REQUIRED_FIELDS:
            if field not in meta:
                errors.append(f"missing-field: {rel} missing frontmatter field '{field}'")
    return errors


def _check_wikilinks(
    wiki_dir: Path, md_files: list[Path]
) -> tuple[list[str], dict[Path, int]]:
    errors = []
    inbound: dict[Path, int] = {f: 0 for f in md_files}

    for f in md_files:
        rel = str(f.relative_to(wiki_dir))
        content = f.read_text()

        # Extract body (after frontmatter)
        if content.startswith("---\n"):
            parts = content.split("---\n", 2)
            body = parts[2] if len(parts) >= 3 else ""
        else:
            body = content

        links = re.findall(r"\[\[([^\]|]+)", body)
        for link in links:
            target = wiki_dir / f"{link}.md"
            if target.exists():
                inbound[target] = inbound.get(target, 0) + 1
            elif not (wiki_dir / link).exists():
                errors.append(f"broken-link: {rel} → [[{link}]] does not resolve to a file")

            # Check absolute path requirement
            if "/" not in link:
                if not (wiki_dir / f"{link}.md").exists():
                    errors.append(
                        f"relative-link: {rel} → [[{link}]] should use absolute path (e.g., [[folder/{link}]])"
                    )

    return errors, inbound


def _check_orphans(
    wiki_dir: Path, md_files: list[Path], inbound: dict[Path, int]
) -> list[str]:
    if len(md_files) <= 1:
        return []
    errors = []
    for f in md_files:
        if inbound.get(f, 0) == 0:
            rel = str(f.relative_to(wiki_dir))
            errors.append(f"orphan: {rel} has no inbound links")
    return errors


def _check_alias_collisions(index: dict) -> list[str]:
    errors = []
    seen: dict[str, str] = {}
    for path, entry in index.items():
        for alias in entry.get("aliases", []):
            alias_lower = alias.lower()
            if alias_lower in seen and seen[alias_lower] != path:
                errors.append(
                    f'alias-collision: "{alias}" claimed by both {seen[alias_lower]} and {path}'
                )
            seen[alias_lower] = path
        title_lower = entry.get("title", "").lower()
        if title_lower and title_lower in seen and seen[title_lower] != path:
            errors.append(
                f'alias-collision: title "{entry["title"]}" collides with alias in {seen[title_lower]}'
            )
        if title_lower:
            seen[title_lower] = path
    return errors


def _check_slugs(wiki_dir: Path, md_files: list[Path]) -> list[str]:
    errors = []
    for f in md_files:
        rel = str(f.relative_to(wiki_dir))
        content = f.read_text()
        meta, _ = parse_frontmatter(content)
        title = meta.get("title", "")
        if not title:
            continue
        expected = slugify(title)
        actual = f.stem
        if expected != actual:
            errors.append(
                f"slug-mismatch: {rel} filename '{actual}' doesn't match slugified title '{expected}'"
            )
    return errors


def _check_flashcard_ids(wiki_dir: Path, index: dict) -> list[str]:
    errors = []
    for key, entry in index.items():
        page_path = wiki_dir / entry["file"]
        if not page_path.exists():
            continue
        content = page_path.read_text()
        meta, _ = parse_frontmatter(content)
        fm_ids = sorted(str(x) for x in meta.get("flashcard_ids", []))
        index_ids = sorted(str(x) for x in entry.get("flashcard_ids", []))
        if fm_ids != index_ids:
            errors.append(
                f"flashcard-mismatch: {entry['file']} frontmatter has {len(fm_ids)} IDs but index has {len(index_ids)}"
            )
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki linter")
    parser.add_argument("wiki_dir", nargs="?", default="wiki", help="Wiki directory")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    md_files = sorted(
        p for p in wiki_dir.rglob("*.md") if ".obsidian" not in p.parts
    )
    errors = lint_wiki(wiki_dir)

    if not errors:
        print(f"lint: wiki is clean ({len(md_files)} pages checked)")
        sys.exit(0)
    else:
        print(f"lint: {len(errors)} issue(s) found in {len(md_files)} pages:")
        print()
        for err in errors:
            print(f"  \u2717 {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
