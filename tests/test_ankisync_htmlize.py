"""Tests for scripts.ankisync.htmlize — markdown/plain card text -> simple Anki HTML.

Anki note fields are HTML (no markdown): literal newlines collapse, backticks
and ** render as-is, and raw angle brackets are parsed as markup. The converter
canonicalizes card text to the simple HTML subset Anki renders everywhere
(<b>, <i>, <code>, <pre>, <ul>/<ol>/<li>, <br>).
"""

from scripts.ankisync.htmlize import to_anki_html


class TestAlreadyHtml:
    def test_html_card_is_untouched(self):
        text = "<div>A cookie is small.<br>Sent via <code>Set-Cookie</code>.</div>"
        assert to_anki_html(text) == text

    def test_list_html_card_is_untouched(self):
        text = "Steps:<ul><li>one</li><li>two</li></ul>"
        assert to_anki_html(text) == text

    def test_idempotent(self):
        text = "line one\nsee `<script>` tags\n**important**"
        once = to_anki_html(text)
        assert to_anki_html(once) == once

    def test_mixed_html_and_markdown_converts_the_markdown(self):
        # some cards were authored with literal <br> plus markdown remnants;
        # markdown converts, the existing HTML (and its raw newlines) stay
        text = '**Nonce:** matches `<script nonce="...">`.<br><br>**Hash:** static.'
        assert to_anki_html(text) == (
            '<b>Nonce:</b> matches <code>&lt;script nonce=&quot;...&quot;&gt;</code>.'
            "<br><br><b>Hash:</b> static."
        )


class TestPlainText:
    def test_newlines_become_br(self):
        assert to_anki_html("line one\nline two") == "line one<br>line two"

    def test_bare_ampersand_and_angles_are_escaped(self):
        assert to_anki_html("a & b, x < y > z") == "a &amp; b, x &lt; y &gt; z"

    def test_existing_entities_are_normalized_not_double_escaped(self):
        # some cards carry entities from an old Anki import (&#x27; = apostrophe)
        assert to_anki_html("user&#x27;s session &amp; cookie") == "user's session &amp; cookie"


class TestInlineCode:
    def test_backticks_become_code(self):
        assert to_anki_html("set `SameSite=Lax` header") == (
            "set <code>SameSite=Lax</code> header"
        )

    def test_html_inside_code_is_escaped(self):
        assert to_anki_html("inject a `<script>` tag") == (
            "inject a <code>&lt;script&gt;</code> tag"
        )

    def test_markdown_inside_code_is_preserved(self):
        assert to_anki_html("`a ** b`") == "<code>a ** b</code>"


class TestCodeFence:
    def test_fence_becomes_pre_code(self):
        # <pre> is a block element: no <br> beside it, or the break doubles
        text = "example:\n```\nif (x < 1) {\n  y();\n}\n```\ndone"
        assert to_anki_html(text) == (
            "example:<pre><code>if (x &lt; 1) {\n  y();\n}</code></pre>done"
        )

    def test_language_hint_is_dropped(self):
        assert to_anki_html("```js\nlet x = 1;\n```") == "<pre><code>let x = 1;</code></pre>"


class TestEmphasis:
    def test_double_asterisk_becomes_b(self):
        assert to_anki_html("**Nonce:** a fresh token") == "<b>Nonce:</b> a fresh token"

    def test_single_asterisk_pair_becomes_i(self):
        assert to_anki_html("the *server* generates it") == "the <i>server</i> generates it"

    def test_lone_asterisk_is_left_alone(self):
        assert to_anki_html("a * b") == "a * b"


class TestLists:
    def test_bullet_lines_become_ul(self):
        assert to_anki_html("two ways:\n- cookie\n- header\nthe end") == (
            "two ways:<ul><li>cookie</li><li>header</li></ul>the end"
        )

    def test_numbered_lines_become_ol(self):
        assert to_anki_html("1. parse\n2. eval") == "<ol><li>parse</li><li>eval</li></ol>"


class TestWikilinks:
    def test_wikilink_becomes_readable_text(self):
        assert to_anki_html("see [[rails/activerecord-preloading]]") == (
            "see <i>activerecord preloading</i>"
        )

    def test_wikilink_with_display_uses_display(self):
        assert to_anki_html("see [[networking/url-anatomy|URL anatomy]]") == (
            "see <i>URL anatomy</i>"
        )
