"""Wiki linter — checks link integrity, frontmatter, absolute paths, orphans, alias collisions."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.wiki.frontmatter import (
    extract_h2s,
    norm_set,
    normalize_heading,
    parse_frontmatter,
    slugify,
)
from scripts.wiki.index import get_wiki_key, iter_wiki_pages, load_index

REQUIRED_FIELDS = {
    "title",
    "aliases",
    "tags",
    "category",
    "created",
    "updated",
    "source_skill",
}

KNOWN_CATEGORIES = {"work", "personal"}

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
# Wikilink not preceded by `!` (image embed). Captures target before any `|display`.
_WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


@dataclass
class ParsedPage:
    path: Path
    rel: str
    raw: str
    meta: dict
    body: str


def _parse_pages(wiki_dir: Path, md_files: list[Path]) -> list[ParsedPage]:
    """Read and parse each page once; shared across all lint checks."""
    pages = []
    for f in md_files:
        raw = f.read_text()
        meta, body = parse_frontmatter(raw)
        pages.append(ParsedPage(f, str(f.relative_to(wiki_dir)), raw, meta, body))
    return pages


def lint_wiki(wiki_dir: Path) -> tuple[list[str], list[str]]:
    """Run all lint checks.

    Returns (errors, warnings). Errors should block CI; warnings are informational.
    """
    wiki_dir = Path(wiki_dir)
    md_files = iter_wiki_pages(wiki_dir)

    if not md_files:
        return [], []

    pages = _parse_pages(wiki_dir, md_files)
    index = load_index(wiki_dir / ".wiki-index.json")

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_check_frontmatter(pages))
    errors.extend(_check_category(pages))
    link_errors, inbound = _check_wikilinks(wiki_dir, pages)
    errors.extend(link_errors)
    warnings.extend(_check_orphans(pages, inbound))
    errors.extend(_check_alias_collisions(index))
    errors.extend(_check_slugs(pages))
    errors.extend(_check_flashcard_ids(pages, index))
    errors.extend(_check_probe_sections(wiki_dir, pages, index))

    return errors, warnings


def _strip_code(body: str) -> str:
    """Remove fenced and inline code so wikilinks inside them aren't linted."""
    body = _FENCED_CODE_RE.sub("", body)
    body = _INLINE_CODE_RE.sub("", body)
    return body


def _check_frontmatter(pages: list[ParsedPage]) -> list[str]:
    errors = []
    for p in pages:
        if not p.raw.startswith("---\n"):
            errors.append(f"missing-frontmatter: {p.rel} has no YAML frontmatter")
            continue
        for field in REQUIRED_FIELDS:
            if field not in p.meta:
                errors.append(f"missing-field: {p.rel} missing frontmatter field '{field}'")
    return errors


def _check_category(pages: list[ParsedPage]) -> list[str]:
    errors = []
    for p in pages:
        if "category" not in p.meta:
            continue
        value = p.meta.get("category")
        if value not in KNOWN_CATEGORIES:
            errors.append(
                f"invalid-category: {p.rel} has category '{value}' (must be one of {sorted(KNOWN_CATEGORIES)})"
            )
    return errors


def _check_wikilinks(
    wiki_dir: Path, pages: list[ParsedPage]
) -> tuple[list[str], dict[Path, int]]:
    errors = []
    inbound: dict[Path, int] = {p.path: 0 for p in pages}
    valid_paths = {p.path for p in pages}

    for p in pages:
        body = _strip_code(p.body)
        for match in _WIKILINK_RE.finditer(body):
            link = match.group(1).strip()
            target = wiki_dir / f"{link}.md"
            target_exists = target in valid_paths
            if target_exists:
                if target != p.path:
                    inbound[target] = inbound.get(target, 0) + 1
            elif not (wiki_dir / link).exists():
                errors.append(f"broken-link: {p.rel} → [[{link}]] does not resolve to a file")

            if "/" not in link and not target_exists:
                errors.append(
                    f"relative-link: {p.rel} → [[{link}]] should use absolute path (e.g., [[folder/{link}]])"
                )

    return errors, inbound


def _check_orphans(pages: list[ParsedPage], inbound: dict[Path, int]) -> list[str]:
    if len(pages) <= 1:
        return []
    warnings = []
    for p in pages:
        if inbound.get(p.path, 0) > 0:
            continue
        if p.meta.get("allow_orphan") is True:
            continue
        warnings.append(f"orphan: {p.rel} has no inbound links")
    return warnings


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


def _check_slugs(pages: list[ParsedPage]) -> list[str]:
    errors = []
    for p in pages:
        title = p.meta.get("title", "")
        if not title:
            continue
        expected = slugify(title)
        actual = p.path.stem
        if expected != actual:
            errors.append(
                f"slug-mismatch: {p.rel} filename '{actual}' doesn't match slugified title '{expected}'"
            )
    return errors


def _check_probe_sections(
    wiki_dir: Path, pages: list[ParsedPage], index: dict
) -> list[str]:
    """Rules:
    - probe-sections-missing: every page must declare non-empty probe_sections.
    - probe-section-unresolved: each probe_sections entry must match an H2 heading.
    - probe-rotation-drift: last_probed must equal probe_sections as a set.
    - probe-index-drift: frontmatter probe_sections must match index probe_sections.
    """
    errors: list[str] = []
    for p in pages:
        if not p.meta:
            continue

        probe_sections = p.meta.get("probe_sections", [])
        last_probed = p.meta.get("last_probed", [])

        if not probe_sections:
            errors.append(f"probe-sections-missing: {p.rel} has no probe_sections")
            continue

        ps_norms = norm_set(probe_sections)
        h2_norms = norm_set(extract_h2s(p.body))
        for sec in probe_sections:
            if normalize_heading(sec) not in h2_norms:
                errors.append(
                    f"probe-section-unresolved: {p.rel} probe_sections entry '{sec}' has no matching H2"
                )

        if last_probed and norm_set(last_probed) != ps_norms:
            errors.append(
                f"probe-rotation-drift: {p.rel} last_probed does not match probe_sections"
            )

        entry = index.get(get_wiki_key(wiki_dir, p.path))
        if entry is not None and norm_set(entry.get("probe_sections", [])) != ps_norms:
            errors.append(
                f"probe-index-drift: {p.rel} frontmatter probe_sections differs from index"
            )

    return errors


def _check_flashcard_ids(pages: list[ParsedPage], index: dict) -> list[str]:
    errors = []
    pages_by_rel = {p.rel: p for p in pages}
    for _key, entry in index.items():
        p = pages_by_rel.get(entry["file"])
        if p is None:
            continue
        fm_ids = sorted(str(x) for x in p.meta.get("flashcard_ids", []))
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
    md_files = iter_wiki_pages(wiki_dir)
    errors, warnings = lint_wiki(wiki_dir)

    if not errors and not warnings:
        print(f"lint: wiki is clean ({len(md_files)} pages checked)")
        sys.exit(0)

    summary = []
    if errors:
        summary.append(f"{len(errors)} error(s)")
    if warnings:
        summary.append(f"{len(warnings)} warning(s)")
    print(f"lint: {', '.join(summary)} in {len(md_files)} pages:")
    print()
    for err in errors:
        print(f"  \u2717 {err}")
    for warn in warnings:
        print(f"  \u26a0 {warn}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
