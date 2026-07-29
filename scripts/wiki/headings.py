"""Title Case rules for wiki headings, shared by the linter and the converter."""

from __future__ import annotations

import re

# Lowercase unless first word or straight after a colon: articles, coordinating
# conjunctions, and short prepositions.
SMALL = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "as", "at", "by",
    "in", "of", "off", "on", "per", "to", "up", "via", "vs", "with", "from", "into", "over",
}
# Case-sensitive identifiers that read as ordinary words and must stay verbatim.
KEEP_VERBATIM = {
    "not", "allOf", "anyOf", "oneOf", "additionalProperties", "strictNullChecks",
    "included", "dependent", "scope", "namespace", "module",
}

_CODE_SPAN = re.compile(r"`[^`]+`")
_IDENTIFIER = re.compile(r"[_()./@#\d]")


def preserve(word: str) -> bool:
    """Leave a word untouched: identifier, acronym, CLI flag, or mixed-case name."""
    core = word.strip(",.:;()\"'")
    return (
        core in KEEP_VERBATIM
        or not core[:1].isalpha()
        or core.isupper()
        or core != core.lower() and core != core.capitalize()
        or bool(_IDENTIFIER.search(word.strip(",;:\"'").rstrip(".")))
    )


def cap(word: str) -> str:
    """Capitalize each hyphen-separated part, keeping small words down.

    depth-first -> Depth-First, observable-to-signal -> Observable-to-Signal
    """
    return "-".join(
        p.lower() if i and p.lower() in SMALL else p[:1].upper() + p[1:]
        for i, p in enumerate(word.split("-"))
    )


def titlecase(text: str) -> str:
    """Title-case a heading, preserving code spans, identifiers, and the first word.

    The first word keeps the author's capitalization on purpose: Title Case would
    otherwise capitalize leading identifiers such as `not`, `on_delete` or `draw`.
    """
    parts = _CODE_SPAN.split(text)
    spans = _CODE_SPAN.findall(text)
    out = []
    for i, part in enumerate(parts):
        done: list[str] = []
        for w in part.split():
            after_colon = bool(done) and done[-1].endswith(":")
            if (i == 0 and not done) or preserve(w):
                done.append(w)
            elif w.strip(",.:;()").lower() in SMALL and not after_colon:
                done.append(w.lower())
            else:
                done.append(cap(w))
        out.append(" ".join(done))
        if i < len(spans):
            out.append(spans[i])
    return re.sub(r"\s+([,.:;])", r"\1", " ".join(s for s in out if s))
