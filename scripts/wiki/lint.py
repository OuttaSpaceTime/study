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
    "created",
    "updated",
    "source_skill",
    "flashcard_ids",
}

# Fields required on content pages only (not on *-index.md MOC files)
CONTENT_REQUIRED_FIELDS = {"next_review", "review_interval", "depth"}

_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"``[^`\n]+``|`[^`\n]+`")
_QUOTED_STR_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MD_SYNTAX_RE = re.compile(r"[*_`\[\]()|#!]+")

_PROSE_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, label, fix)
    (r"\bin order to\b", "in-order-to", "use 'to'"),
    (r"\bit(?:'s| is) worth noting\b", "its-worth-noting", "delete; state it directly"),
    (r"\bit should be noted\b", "it-should-be-noted", "delete"),
    (r"\bdue to the fact that\b", "due-to-the-fact-that", "use 'because'"),
    (r"(?i)^furthermore,", "furthermore", "cut or restructure"),
    (r"(?i)^moreover,", "moreover", "cut or restructure"),
    (r"(?i)^additionally,", "additionally", "cut the filler"),
    (r"\bin conclusion\b", "in-conclusion", "cut"),
    (r"\bseamlessly\b", "seamlessly", "delete or be specific"),
    (r"\butilize[sd]?\b", "utilize", "use 'use'"),
    (r"\bdelve\b", "delve", "use 'explore' or 'read'"),
    (r"—", "em-dash", "split into two sentences"),
    (r"\bis able to\b", "is-able-to", "use 'can'"),
    (r"\bhas the ability to\b", "has-the-ability-to", "use 'can'"),
    (r"\bleverage[sd]?\b", "leverage-verb", "use 'use'"),
    (r"\bthat being said\b", "that-being-said", "cut"),
    (r"\bit goes without saying\b", "it-goes-without-saying", "cut"),
    (r"(?i)^notably,", "notably", "cut or state why it matters"),
    (r"(?i)^essentially,", "essentially", "cut or be specific"),
    (r"\brobust\b", "robust", "name the actual property"),
    (r"\bcomprehensive\b", "comprehensive", "cut or be specific"),
    (r"\bholistic\b", "holistic", "be specific"),
    (r"\bcutting.edge\b", "cutting-edge", "name the technology"),
    (r"\bharness(?:es|ed|ing)?\b", "harness-verb", "use 'use'"),
]
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
    link_errors, inbound = _check_wikilinks(wiki_dir, pages)
    errors.extend(link_errors)
    warnings.extend(_check_orphans(pages, inbound))
    errors.extend(_check_alias_collisions(index))
    errors.extend(_check_slugs(pages))
    errors.extend(_check_flashcard_ids(pages, index))
    errors.extend(_check_probe_sections(wiki_dir, pages, index))
    warnings.extend(_check_moc_coverage(wiki_dir, pages))
    warnings.extend(_check_prose_quality(pages))
    warnings.extend(_check_sentence_fragments(pages))
    warnings.extend(_check_colon_connectors(pages))

    return errors, warnings


def _check_moc_coverage(wiki_dir: Path, pages: list[ParsedPage]) -> list[str]:
    """Warn when MOCs and folders drift out of sync.

    - moc-missing: folder has pages but no <folder>-index.md
    - moc-drift:   folder has a MOC but some non-MOC page isn't listed in it
    """
    warnings: list[str] = []
    by_folder: dict[str, list[ParsedPage]] = {}
    for p in pages:
        parent = p.path.parent
        if parent.parent != wiki_dir:
            continue
        by_folder.setdefault(parent.name, []).append(p)

    for folder, folder_pages in by_folder.items():
        moc_name = f"{folder}-index.md"
        moc = next((p for p in folder_pages if p.path.name == moc_name), None)
        siblings = [p for p in folder_pages if p.path.name != moc_name]
        if moc is None:
            if siblings:
                warnings.append(
                    f"moc-missing: folder '{folder}' has {len(siblings)} page(s) but no {moc_name}"
                )
            continue
        listed = set(_WIKILINK_RE.findall(_strip_code(moc.body)))
        for sib in siblings:
            expected = f"{folder}/{sib.path.stem}"
            if expected not in listed:
                warnings.append(
                    f"moc-drift: {sib.rel} not listed in {folder}/{moc_name}"
                )
    return warnings


def _strip_code(body: str) -> str:
    """Remove fenced and inline code so wikilinks inside them aren't linted."""
    body = _FENCED_CODE_RE.sub("", body)
    body = _INLINE_CODE_RE.sub("", body)
    return body


def _check_prose_quality(pages: list[ParsedPage]) -> list[str]:
    """Warn on common weak prose patterns in wiki body text.

    Operates on p.body (after frontmatter is stripped) and strips code blocks
    before scanning so patterns inside code are not flagged.
    """
    warnings: list[str] = []
    for p in pages:
        prose = _strip_code(p.body)
        for pattern, label, fix in _PROSE_PATTERNS:
            matches = re.findall(pattern, prose, re.MULTILINE)
            if matches:
                n = len(matches)
                warnings.append(
                    f"prose-quality: {p.rel} [{label}] ({n}x) — {fix}"
                )
    return warnings


def _word_count_prose(text: str) -> int:
    """Count words in a prose fragment after stripping markdown inline syntax."""
    clean = _MD_SYNTAX_RE.sub(" ", text)
    return len(clean.split())


_ABBREV_ENDS_RE = re.compile(r"\b(vs|e\.g|i\.e|etc|cf|no|pp|vol|ed|fig|approx)\.?\s*$", re.IGNORECASE)


def _check_sentence_fragments(pages: list[ParsedPage]) -> list[str]:
    """Warn on ≤3-word sentences immediately followed by a lowercase continuation.

    This targets the specific bad pattern left by mechanical colon removal:
        "The practical takeaway. **for long-context requests..."
    Valid short sentences like "Both are needed. An id alone..." are not flagged
    because their continuation starts with an uppercase letter.
    """
    warnings = []
    for p in pages:
        lines = p.body.split("\n")
        in_code = False
        hits = 0
        for raw_line in lines:
            if re.match(r"\s*```", raw_line):
                in_code = not in_code
                continue
            if in_code:
                continue
            # Replace inline code with "X" to preserve case of surrounding text
            line = _INLINE_CODE_RE.sub("X", raw_line)
            line = _QUOTED_STR_RE.sub("X", line)
            s = line.lstrip()
            if not s:
                continue
            if s[0] == "#":
                continue
            if re.match(r"^[-*]\s", s) or re.match(r"^\d+\.\s", s):
                continue
            if s.startswith(">") or s.startswith("|"):
                continue
            parts = _SENT_SPLIT_RE.split(s)
            for part, nxt in zip(parts[:-1], parts[1:]):
                if _word_count_prose(part) > 3:
                    continue
                if _ABBREV_ENDS_RE.search(part):
                    continue
                nxt_clean = _MD_SYNTAX_RE.sub("", nxt).lstrip()
                if nxt_clean and nxt_clean[0].islower():
                    hits += 1
        if hits:
            warnings.append(
                f"sentence-fragment: {p.rel} ({hits}x) — short sentence (≤3 words) followed by lowercase; likely a prose fragment"
            )
    return warnings


# Lines that legitimately follow an end-of-line colon
_EOL_COLON_OK = re.compile(r"^(```|>\s|[-*]\s|\d+\.\s|!\[\[|\|)")


def _check_colon_connectors(pages: list[ParsedPage]) -> list[str]:
    """Warn on colons used as prose clause connectors.

    Acceptable: heading (## ...), list-item term separator (- term: desc),
    end-of-line colon introducing a code fence / blockquote / list / table / image.
    Not acceptable: colon connecting two prose clauses on the same line,
    or end-of-line colon followed by a plain prose continuation.

    Uses a line-by-line state machine instead of pre-stripping the body so that
    EOL-colon lookahead always reads the *original* next line. Pre-stripping
    removes code blocks, which makes whatever comes *after* the block appear to
    immediately follow the colon — a common source of false positives.
    """
    warnings = []
    for p in pages:
        lines = p.body.split("\n")
        in_code = False
        hits = 0

        for i, raw_line in enumerate(lines):
            # Track fenced code block state; skip all content inside blocks.
            if re.match(r"\s*```", raw_line):
                in_code = not in_code
                continue
            if in_code:
                continue

            # Per-line: strip inline code and quoted strings before checking.
            line = _INLINE_CODE_RE.sub("X", raw_line)
            line = _QUOTED_STR_RE.sub("X", line)
            s = line.lstrip()

            if not s:
                continue
            if s[0] == "#":  # heading
                continue
            if re.match(r"^[-*]\s", s) or re.match(r"^\d+\.\s", s):  # list items
                continue
            if s.startswith(">") or s.startswith("|"):  # blockquote / table
                continue

            # End-of-line colon: walk forward in the *original* lines, tracking
            # code block state, to find what actually follows the colon.
            if s.rstrip().endswith(":"):
                next_s = ""
                inner_code = False
                for j in range(i + 1, len(lines)):
                    jl = lines[j]
                    if re.match(r"\s*```", jl):
                        inner_code = not inner_code
                        if inner_code:
                            # An opening fence means a code block follows — colon is fine.
                            next_s = jl.lstrip()
                            break
                        continue
                    if inner_code:
                        continue
                    if jl.strip():
                        nxt = _INLINE_CODE_RE.sub("X", jl.lstrip())
                        nxt = _QUOTED_STR_RE.sub("X", nxt)
                        next_s = nxt
                        break
                if next_s and not _EOL_COLON_OK.match(next_s):
                    hits += 1
                continue

            # Mid-line ': ' — prose connector.
            if ": " in s:
                if "://" in s and ": " not in re.sub(r"https?://\S+", "", s):
                    continue
                hits += 1

        if hits:
            warnings.append(
                f"prose-colon: {p.rel} ({hits}x) — split into sentences; "
                "colon only before code/quote/list/table/image"
            )
    return warnings


def _check_frontmatter(pages: list[ParsedPage]) -> list[str]:
    errors = []
    for p in pages:
        if not p.raw.startswith("---\n"):
            errors.append(f"missing-frontmatter: {p.rel} has no YAML frontmatter")
            continue
        for field in REQUIRED_FIELDS:
            if field not in p.meta:
                errors.append(f"missing-field: {p.rel} missing frontmatter field '{field}'")
        if not p.path.stem.endswith("-index"):
            for field in CONTENT_REQUIRED_FIELDS:
                if field not in p.meta:
                    errors.append(f"missing-field: {p.rel} missing frontmatter field '{field}'")
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
