"""Prose checks: the warnings. Style patterns, heading case, density, fragments.

They never fail a lint run; a page can opt out of one with `lint_ignore` (see runner.py).
"""

from __future__ import annotations

import re
import statistics

from scripts.wiki.headings import titlecase
from scripts.wiki.links import FENCED_CODE_RE as _FENCED_CODE_RE
from scripts.wiki.links import INLINE_CODE_RE as _INLINE_CODE_RE
from scripts.wiki.links import strip_code as _strip_code
from scripts.wiki.lint.page import ParsedPage

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


def prose_warnings(pages: list[ParsedPage]) -> list[str]:
    """Every warning-level check, in the order lint reports them."""
    warnings: list[str] = []
    warnings.extend(_check_prose_quality(pages))
    warnings.extend(_check_sentence_fragments(pages))
    warnings.extend(_check_prose_density(pages))
    warnings.extend(_check_heading_case(pages))
    warnings.extend(_check_colon_connectors(pages))
    return warnings
