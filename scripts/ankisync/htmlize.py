"""Convert markdown/plain card text to the simple HTML subset Anki renders.

Anki note fields are HTML: literal newlines collapse, backticks and ** show
as-is, and raw angle brackets are parsed as markup (a literal <script> example
disappears or executes). Target subset: <b>, <i>, <code>, <pre>, <ul>/<ol>/<li>,
<br> — renders identically on desktop, AnkiDroid, and AnkiWeb.

Cards that already contain structural HTML are returned unchanged, which also
makes the conversion idempotent.
"""

import html
import re

_HTML_MARKER = re.compile(r"</code>|<br\s*/?>|<div[ >]|<ul>|<ol>|<li>|</b>|</strong>|<pre[ >]")
_FENCE = re.compile(r"```[^\n]*\n(.*?)\n?```", re.S)
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*([^*\s][^*\n]*?)\*(?![\w*])")
_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
_BULLET = re.compile(r"^\s*[-*] (.*)$")
_NUMBERED = re.compile(r"^\s*\d+\. (.*)$")


def _wikilink_text(m: re.Match) -> str:
    display = m.group(2) or m.group(1).rsplit("/", 1)[-1].replace("-", " ")
    return f"<i>{display}</i>"


def _lists_to_html(lines: list[str]) -> list[str]:
    out: list[str] = []
    open_tag = None  # "ul" | "ol" | None
    for line in lines:
        for tag, pat in (("ul", _BULLET), ("ol", _NUMBERED)):
            m = pat.match(line)
            if m:
                if open_tag != tag:
                    if open_tag:
                        out.append(f"</{open_tag}>")
                    out.append(f"<{tag}>")
                    open_tag = tag
                out.append(f"<li>{m.group(1)}</li>")
                break
        else:
            if open_tag:
                out.append(f"</{open_tag}>")
                open_tag = None
            out.append(line + "\n")
    if open_tag:
        out.append(f"</{open_tag}>")
    return out


def to_anki_html(text: str) -> str:
    is_html = bool(_HTML_MARKER.search(text))

    if not is_html:
        # normalize entities left over from old Anki imports (&#x27; etc.) to the
        # literal character, then re-escape once below — avoids double-escaping
        text = html.unescape(text)

    # protect code content from escaping/markdown passes via placeholders
    stash: list[str] = []

    def _stash(rendered: str) -> str:
        stash.append(rendered)
        return f"\x00{len(stash) - 1}\x00"

    # markdown constructs convert in every card — including mixed cards that
    # were authored with literal <br>/<div> plus markdown remnants
    text = _FENCE.sub(lambda m: _stash(f"<pre><code>{html.escape(m.group(1))}</code></pre>"), text)
    text = _INLINE_CODE.sub(lambda m: _stash(f"<code>{html.escape(m.group(1))}</code>"), text)
    text = _WIKILINK.sub(_wikilink_text, text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _ITALIC.sub(r"<i>\1</i>", text)

    if not is_html:
        # plain cards: escape bare markup chars and turn structure into HTML;
        # in HTML cards the remaining angle brackets/newlines ARE the markup
        text = _escape_outside_stash(text)
        text = "".join(_lists_to_html(text.split("\n"))).rstrip("\n")
        text = text.replace("\n", "<br>")

    text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    # block elements carry their own breaks; <br> directly against them doubles up
    text = re.sub(r"<br>(<ul>|<ol>|<pre>)", r"\1", text)
    text = re.sub(r"(</ul>|</ol>|</pre>)<br>", r"\1", text)
    return text


def _escape_outside_stash(text: str) -> str:
    # placeholders contain no &/<,>; tags produced above (<b>, <i>) must survive
    parts = re.split(r"(<b>|</b>|<i>|</i>)", text)
    return "".join(p if p in ("<b>", "</b>", "<i>", "</i>") else html.escape(p, quote=False)
                   for p in parts)
