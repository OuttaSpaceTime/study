"""Structure checks: the errors. Frontmatter, links, slugs and index agreement.

These decide whether a page is well-formed; prose.py only advises on style.
"""

from __future__ import annotations

from pathlib import Path

from scripts.wiki.frontmatter import slugify
from scripts.wiki.links import WIKILINK_RE as _WIKILINK_RE
from scripts.wiki.links import strip_code as _strip_code
from scripts.wiki.lint.page import ParsedPage

REQUIRED_FIELDS = {
    "title",
    "aliases",
    "tags",
    "created",
    "updated",
    "source_skill",
    "flashcard_ids",
}

OPTIONAL_FIELDS = {"lint_ignore", "explorables"}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

# Named so the error can say what replaced them. Anything else unrecognized is
# reported generically by the same check.
RETIRED_FIELDS = {
    "next_review": "wiki pages are no longer scheduled",
    "review_interval": "wiki pages are no longer scheduled",
    "last_deepened": "use 'updated'",
    "depth": "dropped with the old walkthrough depth model",
    "probe_sections": "probe sections were removed",
    "last_probed": "probe sections were removed",
    "allow_orphan": "the orphan check went with the index pages",
}


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


def _check_forbidden_fields(pages: list[ParsedPage]) -> list[str]:
    """Frontmatter is a closed schema, so retired fields cannot quietly return.

    An allowlist rather than a denylist: every retirement so far (scheduling,
    probe sections, depth) would otherwise have needed its own entry, and the
    one that got missed is the one that comes back.
    """
    errors: list[str] = []
    for p in pages:
        for field in sorted(set(p.meta) - ALLOWED_FIELDS):
            reason = RETIRED_FIELDS.get(field, "not part of the page schema")
            errors.append(f"forbidden-field: {p.rel} carries '{field}' ({reason})")
    return errors


def _check_explorables(pages: list[ParsedPage]) -> list[str]:
    """`explorables` must be a list of https URLs: Omvida opens each one as is,
    so a bare id or a local path would give a button that opens nothing."""
    errors: list[str] = []
    for p in pages:
        if "explorables" not in p.meta:
            continue
        value = p.meta["explorables"]
        if not isinstance(value, list):
            errors.append(f"bad-explorable: {p.rel} 'explorables' must be a list of URLs")
            continue
        for url in value:
            if not (isinstance(url, str) and url.startswith("https://")):
                errors.append(f"bad-explorable: {p.rel} explorable '{url}' is not an https URL")
    return errors


def _check_aliases(pages: list[ParsedPage]) -> list[str]:
    """Aliases must not be single-letter abbreviations (per wiki-write-protocol)."""
    errors: list[str] = []
    for p in pages:
        for alias in p.meta.get("aliases") or []:
            if isinstance(alias, str) and len(alias.strip()) == 1:
                errors.append(
                    f"alias-too-short: {p.rel} alias '{alias}' is a single character; use a longer alias"
                )
    return errors


def _check_wikilinks(wiki_dir: Path, pages: list[ParsedPage]) -> list[str]:
    errors = []
    valid_paths = {p.path for p in pages}

    for p in pages:
        body = _strip_code(p.body)
        for match in _WIKILINK_RE.finditer(body):
            link = match.group(1).strip()
            target = wiki_dir / f"{link}.md"
            target_exists = target in valid_paths
            if not target_exists and not (wiki_dir / link).exists():
                errors.append(f"broken-link: {p.rel} → [[{link}]] does not resolve to a file")

            if "/" not in link and not target_exists:
                errors.append(
                    f"relative-link: {p.rel} → [[{link}]] should use absolute path (e.g., [[folder/{link}]])"
                )

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


def structure_errors(wiki_dir: Path, pages: list[ParsedPage], index: dict) -> list[str]:
    """Every error-level check, in the order lint reports them."""
    errors: list[str] = []
    errors.extend(_check_frontmatter(pages))
    errors.extend(_check_forbidden_fields(pages))
    errors.extend(_check_explorables(pages))
    errors.extend(_check_aliases(pages))
    errors.extend(_check_wikilinks(wiki_dir, pages))
    errors.extend(_check_alias_collisions(index))
    errors.extend(_check_slugs(pages))
    errors.extend(_check_flashcard_ids(pages, index))
    return errors
