"""Wiki linter — checks link integrity, frontmatter, absolute paths, alias collisions."""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter, slugify
from scripts.wiki.headings import titlecase
from scripts.wiki.index import iter_wiki_pages, load_index
from scripts.wiki.links import FENCED_CODE_RE as _FENCED_CODE_RE
from scripts.wiki.links import INLINE_CODE_RE as _INLINE_CODE_RE
from scripts.wiki.links import WIKILINK_RE as _WIKILINK_RE
from scripts.wiki.links import strip_code as _strip_code

REQUIRED_FIELDS = {
    "title",
    "aliases",
    "tags",
    "created",
    "updated",
    "source_skill",
    "flashcard_ids",
}

OPTIONAL_FIELDS = {"lint_ignore"}
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

_QUOTED_STR_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_MD_SYNTAX_RE = re.compile(r"[*_`\[\]()|#!]+")
# Matches markdown/wikilinks with an optional following colon: [[target]]:, [text](url):, [text].
# Stripping these before the prose-colon check allows colons inside or after link brackets.
_LINK_COLON_RE = re.compile(r"(?:\[\[[^\]]*\]\]|\[[^\]]*\]\([^)]*\)|\[[^\]]*\])(?:\s*:\s*)?")

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
    (
        r"(?i)\bnot (?:just|only|merely|simply)\b[^.]{0,60}\bbut\b"
        r"|\b(?:it|this|that)(?:'s| is) not\b[^.]{0,40}\.\s+(?:it|this|that)(?:'s| is)\b",
        "negative-parallelism",
        "state what it is; drop the contrast scaffold",
    ),
    (
        r",\s+(?:ensuring|allowing|enabling|providing|highlighting|underscoring"
        r"|reflecting|showcasing|emphasizing|resulting in|making it)\b",
        "trailing-participle",
        "make it its own sentence or cut it",
    ),
    (r"\b(?:serves|functions|acts) as\b|\bboasts\b", "copula-avoidance", "use 'is' or 'has'"),
    (
        r"(?i)^(?:however|therefore|thus|consequently|ultimately|crucially"
        r"|importantly|interestingly|overall|in summary|instead),",
        "conjunctive-opener",
        "cut the connector or restructure",
    ),
    (
        r"(?i)\b(?:studies show|research shows|experts (?:say|argue|agree)"
        r"|industry reports suggest|it is widely (?:regarded|considered|believed))\b",
        "vague-attribution",
        "name the source or cut the claim",
    ),
]


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


def lint_wiki(
    wiki_dir: Path,
    dirty_pages: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Run all lint checks.

    Returns (errors, warnings). Errors should block CI; warnings are informational.

    Per-page `lint_ignore` frontmatter suppresses named **warnings** for that page,
    but only while the page is committed (not dirty in git) — see `_apply_lint_ignore`.
    `dirty_pages` (rel paths under `wiki_dir`) is computed from git when omitted;
    pass an explicit set to make the suppression deterministic in tests.
    """
    wiki_dir = Path(wiki_dir)
    if dirty_pages is None:
        dirty_pages = _dirty_wiki_pages(wiki_dir)
    md_files = iter_wiki_pages(wiki_dir)

    if not md_files:
        return [], []

    pages = _parse_pages(wiki_dir, md_files)
    index = load_index(wiki_dir / ".wiki-index.json")

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_check_frontmatter(pages))
    errors.extend(_check_forbidden_fields(pages))
    errors.extend(_check_aliases(pages))
    errors.extend(_check_wikilinks(wiki_dir, pages))
    errors.extend(_check_alias_collisions(index))
    errors.extend(_check_slugs(pages))
    errors.extend(_check_flashcard_ids(pages, index))
    warnings.extend(_check_prose_quality(pages))
    warnings.extend(_check_sentence_fragments(pages))
    warnings.extend(_check_prose_density(pages))
    warnings.extend(_check_heading_case(pages))
    warnings.extend(_check_colon_connectors(pages))

    warnings = _apply_lint_ignore(warnings, pages, dirty_pages)

    return errors, warnings


def _dirty_wiki_pages(wiki_dir: Path) -> set[str]:
    """Return wiki-relative paths that have uncommitted git changes.

    Includes modified, staged, and untracked files. Returns an empty set when
    `wiki_dir` is not inside a git repo or git is unavailable — so suppression
    falls back to "treat as clean" rather than crashing lint.
    """
    try:
        top = subprocess.run(
            ["git", "-C", str(wiki_dir), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if top.returncode != 0:
            return set()
        root = Path(top.stdout.strip())
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if status.returncode != 0:
            return set()
    except (OSError, subprocess.SubprocessError):
        return set()

    dirty: set[str] = set()
    for line in status.stdout.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:]
        # Renames are reported as "old -> new"; the new path is what's on disk.
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        abs_path = (root / path_part.strip().strip('"')).resolve()
        try:
            dirty.add(str(abs_path.relative_to(wiki_dir.resolve())))
        except ValueError:
            continue  # outside the wiki tree
    return dirty


def _warning_label_and_target(warning: str) -> tuple[str, str]:
    """Split a warning string into its `label` and the page rel-path it concerns.

    Warnings are formatted `"<label>: <rel> ..."`. A warning whose second token
    is not a page path simply won't match any page's lint_ignore, so it is never
    suppressed by accident.
    """
    label, _, rest = warning.partition(": ")
    target = rest.split(maxsplit=1)[0] if rest else ""
    return label, target


def _apply_lint_ignore(
    warnings: list[str], pages: list[ParsedPage], dirty_pages: set[str]
) -> list[str]:
    """Drop warnings a page opted out of via `lint_ignore`, unless the page is dirty.

    `lint_ignore` is a frontmatter list of warning labels (e.g. `heading-case`).
    The opt-out only holds while the page is committed: a page with uncommitted
    changes still gets all its warnings, so the decision to ignore must itself be
    committed before it takes effect, and editing the page re-surfaces the rule.
    Only warnings are suppressible; errors are never filtered.
    """
    ignore_map: dict[str, set[str]] = {}
    for p in pages:
        rules = p.meta.get("lint_ignore") or []
        if isinstance(rules, list):
            ignored = {str(r) for r in rules}
            if ignored:
                ignore_map[p.rel] = ignored

    if not ignore_map:
        return warnings

    kept: list[str] = []
    for w in warnings:
        label, target = _warning_label_and_target(w)
        ignored = ignore_map.get(target)
        if ignored and label in ignored and target not in dirty_pages:
            continue
        kept.append(w)
    return kept


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


_HEDGE_RE = re.compile(
    r"\b(?:may|might|could|would|can(?!['’]t)|tends? to|typically|generally|often"
    r"|usually|in some cases|depending on|arguably|somewhat|relatively)\b",
    re.IGNORECASE,
)
MAX_HEDGES_PER_1000_WORDS = 15
# Below this count one hedge word swings the rate by more than the threshold's own
# precision, so the rate is not resolvable enough to act on.
MIN_HEDGES_FOR_RATE = 8
UNIFORM_MEAN_WORDS = 16
UNIFORM_STDEV_WORDS = 6.5
_BULLET_RE = re.compile(r"^\s*(?:[-*+] |\d+\. )")
MAX_BULLET_SHARE = 0.60
MIN_WORDS_FOR_BULLET_SHARE = 400


def _bullet_share(body: str) -> tuple[int, float]:
    """Return (non-code word count, fraction of those words sitting in list items)."""
    bullet = other = 0
    for ln in _strip_code(body).splitlines():
        s = ln.strip()
        if not s or s.startswith(("#", ">", "|")):
            continue
        if _BULLET_RE.match(ln):
            bullet += _word_count_prose(s)
        else:
            other += _word_count_prose(s)
    total = bullet + other
    return total, (bullet / total if total else 0.0)


def _prose_sentences(body: str) -> tuple[str, list[int]]:
    """Return (flowing prose, sentence word counts) with code, headings and lists removed."""
    prose = "\n".join(
        ln for ln in _strip_code(body).splitlines()
        if ln.strip() and not ln.lstrip().startswith(("#", ">", "|", "-", "*"))
    )
    lengths = [n for s in _SENT_SPLIT_RE.split(prose) if (n := _word_count_prose(s)) >= 3]
    return prose, lengths


def _check_heading_case(pages: list[ParsedPage]) -> list[str]:
    """Warn on headings that are not in Title Case.

    A heading passes when it is already a fixed point of `titlecase`, so the linter
    and `scripts/wiki/headings.py` can never disagree about what conforms.
    """
    warnings: list[str] = []
    for p in pages:
        bad = [
            m.group(1)
            for ln in _FENCED_CODE_RE.sub("", p.body).splitlines()
            if (m := re.match(r"^#{2,}\s+(.+?)\s*$", ln))
            and titlecase(m.group(1)) != m.group(1)
        ]
        if bad:
            warnings.append(
                f"heading-case: {p.rel} ({len(bad)}x) — use Title Case, e.g. "
                f"'{bad[0]}' -> '{titlecase(bad[0])}'"
            )
    return warnings


def _check_prose_density(pages: list[ParsedPage]) -> list[str]:
    """Warn on per-page prose statistics that no single-phrase pattern can see.

    Both checks need enough flowing prose to be a signal, so short and list-heavy
    pages are skipped. Uniformity requires a high mean length as well as a low
    spread: terse pages are meant to have short, even sentences.
    """
    warnings: list[str] = []
    for p in pages:
        total, share = _bullet_share(p.body)
        if total >= MIN_WORDS_FOR_BULLET_SHARE and share > MAX_BULLET_SHARE:
            warnings.append(
                f"bullet-dominance: {p.rel} ({share:.0%} of words in list items) — "
                f"write the connections between the points as prose"
            )
        prose, lengths = _prose_sentences(p.body)
        words = _word_count_prose(prose)
        if words < 80 or len(lengths) < 8:
            continue
        hedges = len(_HEDGE_RE.findall(prose))
        rate = 1000 * hedges / words
        if hedges >= MIN_HEDGES_FOR_RATE and rate > MAX_HEDGES_PER_1000_WORDS:
            warnings.append(
                f"hedge-density: {p.rel} ({rate:.0f} per 1000 words) — "
                f"cut modals and qualifiers; state what happens"
            )
        mean, stdev = statistics.mean(lengths), statistics.stdev(lengths)
        if mean >= UNIFORM_MEAN_WORDS and stdev < UNIFORM_STDEV_WORDS:
            warnings.append(
                f"sentence-uniformity: {p.rel} (mean {mean:.0f} words, stdev {stdev:.1f}) — "
                f"vary sentence length; break up the long ones"
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
            for part, nxt in zip(parts[:-1], parts[1:], strict=False):
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
                # Allow colon immediately following a closing bracket (link/wikilink descriptor).
                if ": " not in _LINK_COLON_RE.sub("", s):
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
