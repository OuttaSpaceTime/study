// Tests for lib/markdown.ts.
//
// Layer 1: pure units (slugifyHeading, stripLeadingH1, createWikilinkResolver).
// Layer 2: end-to-end through the real pipeline, mirroring how
// components/article/ArticleBody.tsx wires it: react-markdown + remark-gfm +
// remarkWikilinks with a resolver built via createWikilinkResolver, rendered
// with react-dom/server's renderToStaticMarkup.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  createWikilinkResolver,
  remarkCallouts,
  remarkWikilinks,
  slugifyHeading,
  stripLeadingH1,
} from "@/lib/markdown";
import type { PageMeta } from "@/lib/types";

/** Minimal PageMeta stub; the resolver only reads `path` and `slug`. */
function makePage(path: string): PageMeta {
  const segments = path.split("/");
  const slug = segments[segments.length - 1] ?? path;
  return {
    path,
    folder: segments.slice(0, -1).join("/"),
    slug,
    title: slug,
    aliases: [],
    tags: [],
    created: "2026-01-01",
    updated: "2026-01-01",
    nextReview: "",
    reviewInterval: null,
    depth: null,
    isIndex: false,
    sections: [],
    outbound: [],
    inbound: [],
  };
}

/** Render markdown through the same plugin stack ArticleBody uses. */
function render(markdown: string, paths: readonly string[]): string {
  const resolve = createWikilinkResolver(paths.map(makePage));
  return renderToStaticMarkup(
    <Markdown remarkPlugins={[remarkGfm, [remarkWikilinks, { resolve }]]}>
      {markdown}
    </Markdown>,
  );
}

/** Render markdown through remark-gfm + remarkCallouts, as ArticleBody does. */
function renderCallout(markdown: string): string {
  return renderToStaticMarkup(
    <Markdown remarkPlugins={[remarkGfm, remarkCallouts]}>{markdown}</Markdown>,
  );
}

describe("remarkCallouts", () => {
  it("tags a `> [Note] ...` blockquote with callout classes and a title", () => {
    const html = renderCallout("> [Note] Body text here.");
    expect(html).toContain('class="callout callout-note"');
    expect(html).toContain('<p class="callout-title">Note</p>');
    expect(html).toContain("Body text here.");
    expect(html).not.toContain("[Note]");
  });

  it("lowercases the type but keeps the original label casing", () => {
    const html = renderCallout("> [Warning] Careful.");
    expect(html).toContain('class="callout callout-warning"');
    expect(html).toContain('<p class="callout-title">Warning</p>');
  });

  it("handles a custom label like [Heuristic]", () => {
    const html = renderCallout("> [Heuristic] A rule of thumb.");
    expect(html).toContain('class="callout callout-heuristic"');
    expect(html).toContain('<p class="callout-title">Heuristic</p>');
  });

  it("leaves a plain blockquote untouched", () => {
    const html = renderCallout("> Just an ordinary quote.");
    expect(html).not.toContain("callout");
    expect(html).toContain("Just an ordinary quote.");
  });

  it("does not treat a mid-paragraph bracket as a marker", () => {
    const html = renderCallout("> Text with [Note] in the middle.");
    expect(html).not.toContain("callout");
    expect(html).toContain("[Note]");
  });
});

describe("slugifyHeading", () => {
  it("lowercases and replaces spaces with hyphens", () => {
    expect(slugifyHeading("Hello World")).toBe("hello-world");
  });

  it("drops special characters", () => {
    expect(slugifyHeading("What's New? (v2.0)")).toBe("whats-new-v20");
  });

  it("collapses runs of spaces and hyphens into a single hyphen", () => {
    expect(slugifyHeading("Foo --  Bar")).toBe("foo-bar");
  });

  it("trims surrounding whitespace", () => {
    expect(slugifyHeading("  Padded Heading  ")).toBe("padded-heading");
  });

  it("keeps digits and existing hyphens", () => {
    expect(slugifyHeading("HTTP/2 Server-Push")).toBe("http2-server-push");
  });

  it("passes already-slugified input through unchanged", () => {
    expect(slugifyHeading("already-a-slug")).toBe("already-a-slug");
  });
});

describe("stripLeadingH1", () => {
  it("strips the first H1 line and keeps the body", () => {
    expect(stripLeadingH1("# Title\n\nBody here.")).toBe("Body here.");
  });

  it("strips an H1 preceded by blank lines", () => {
    expect(stripLeadingH1("\n\n# Title\nBody")).toBe("Body");
  });

  it("is a no-op when the document has no leading H1", () => {
    const md = "Just a paragraph.\n\nMore text.";
    expect(stripLeadingH1(md)).toBe(md);
  });

  it("does not strip an H2", () => {
    const md = "## Section\nBody";
    expect(stripLeadingH1(md)).toBe(md);
  });

  it("does not strip an H1 that appears after other content", () => {
    const md = "Intro paragraph.\n\n# Later Heading\nBody";
    expect(stripLeadingH1(md)).toBe(md);
  });

  it("strips only the first of two consecutive H1 lines", () => {
    expect(stripLeadingH1("# One\n# Two\nBody")).toBe("# Two\nBody");
  });

  it("returns an empty string for an H1-only document", () => {
    expect(stripLeadingH1("# Only Title")).toBe("");
  });

  it("requires a space or tab after the hash", () => {
    const md = "#NoSpace heading\nBody";
    expect(stripLeadingH1(md)).toBe(md);
  });
});

describe("createWikilinkResolver", () => {
  it("resolves an exact path match", () => {
    const resolve = createWikilinkResolver([makePage("a/b"), makePage("c/d")]);
    expect(resolve("a/b")).toBe("a/b");
  });

  it("resolves a bare slug when it is unique", () => {
    const resolve = createWikilinkResolver([makePage("a/b"), makePage("c/d")]);
    expect(resolve("b")).toBe("a/b");
  });

  it("returns null for an ambiguous slug", () => {
    const resolve = createWikilinkResolver([makePage("a/b"), makePage("c/b")]);
    expect(resolve("b")).toBeNull();
  });

  it("still resolves an exact path when the slug is ambiguous", () => {
    const resolve = createWikilinkResolver([makePage("a/b"), makePage("c/b")]);
    expect(resolve("a/b")).toBe("a/b");
    expect(resolve("c/b")).toBe("c/b");
  });

  it("returns null for an unknown target", () => {
    const resolve = createWikilinkResolver([makePage("a/b")]);
    expect(resolve("nope")).toBeNull();
    expect(resolve("no/such")).toBeNull();
  });

  it("treats a path-qualified target without an exact match as broken", () => {
    // Mirrors Obsidian and scripts/lint: the slug fallback applies to bare
    // names only — a wrong folder prefix is never silently corrected.
    const resolve = createWikilinkResolver([makePage("a/b")]);
    expect(resolve("zzz/b")).toBeNull();
  });

  it("resolves MOC targets to their folder view (exact path and bare slug)", () => {
    // MOC pages aren't rendered; links to them land on the folder view.
    const mocs = [{ path: "rails/rails-index", folder: "rails" }];
    const resolve = createWikilinkResolver([makePage("a/b")], mocs);
    expect(resolve("rails/rails-index")).toBe("rails");
    expect(resolve("rails-index")).toBe("rails");
  });

  it("prefers a real page over a MOC for an ambiguous bare slug", () => {
    const mocs = [{ path: "x/shared", folder: "x" }];
    const resolve = createWikilinkResolver([makePage("a/shared")], mocs);
    expect(resolve("shared")).toBe("a/shared");
  });
});

describe("remarkWikilinks end-to-end (react-markdown + remark-gfm)", () => {
  it("converts [[a/b]] to a /wiki link with the wikilink class", () => {
    const html = render("[[a/b]]", ["a/b"]);
    expect(html).toContain('href="/wiki/a/b"');
    expect(html).toMatch(/<a[^>]*class="wikilink"[^>]*>a\/b<\/a>/);
  });

  it("shows the display text for [[a/b|display]]", () => {
    const html = render("[[a/b|display]]", ["a/b"]);
    expect(html).toContain('href="/wiki/a/b"');
    expect(html).toMatch(/<a[^>]*>display<\/a>/);
    expect(html).not.toContain(">a/b<");
  });

  it("appends a slugified heading anchor for [[a/b#Some Heading]]", () => {
    const html = render("[[a/b#Some Heading]]", ["a/b"]);
    expect(html).toContain('href="/wiki/a/b#some-heading"');
    expect(html).toMatch(/<a[^>]*>a\/b#Some Heading<\/a>/);
  });

  it("combines heading anchor and display text", () => {
    const html = render("[[a/b#Some Heading|see here]]", ["a/b"]);
    expect(html).toContain('href="/wiki/a/b#some-heading"');
    expect(html).toMatch(/<a[^>]*>see here<\/a>/);
  });

  it("renders [[#Local Heading]] as a same-page anchor", () => {
    const html = render("[[#Local Heading]]", []);
    expect(html).toContain('href="#local-heading"');
    expect(html).toMatch(/<a[^>]*class="wikilink"[^>]*>#Local Heading<\/a>/);
  });

  it("renders a broken target as a wikilink-broken span", () => {
    const html = render("[[no/such]]", ["a/b"]);
    expect(html).toContain('<span class="wikilink-broken">no/such</span>');
    expect(html).not.toContain("<a ");
  });

  it("renders an ambiguous slug as a wikilink-broken span", () => {
    const html = render("[[b]]", ["a/b", "c/b"]);
    expect(html).toContain('<span class="wikilink-broken">b</span>');
    expect(html).not.toContain("<a ");
  });

  it("leaves embeds ![[a/b]] as literal text", () => {
    const html = render("![[a/b]]", ["a/b"]);
    expect(html).toContain("![[a/b]]");
    expect(html).not.toContain("<a ");
    expect(html).not.toContain("wikilink");
  });

  it("keeps an embed literal while converting a sibling wikilink", () => {
    const html = render("![[a/b]] then [[a/b]]", ["a/b"]);
    expect(html).toContain("![[a/b]] then ");
    expect(html).toMatch(/<a[^>]*href="\/wiki\/a\/b"[^>]*>a\/b<\/a>/);
  });

  it("does not convert wikilinks inside fenced code blocks", () => {
    const html = render("```\n[[a/b]]\n```", ["a/b"]);
    expect(html).toContain("<pre>");
    expect(html).toContain("[[a/b]]");
    expect(html).not.toContain("<a ");
  });

  it("does not convert wikilinks inside inline code", () => {
    const html = render("Use `[[a/b]]` and [[a/b]].", ["a/b"]);
    expect(html).toContain("<code>[[a/b]]</code>");
    // The sibling outside the code span still converts.
    expect(html).toMatch(/<a[^>]*href="\/wiki\/a\/b"[^>]*>a\/b<\/a>/);
  });

  it("converts two wikilinks in one paragraph and preserves surrounding text", () => {
    const html = render("See [[a/b]] and [[c/d]] for more.", ["a/b", "c/d"]);
    expect(html).toMatch(
      /See <a[^>]*href="\/wiki\/a\/b"[^>]*>a\/b<\/a> and <a[^>]*href="\/wiki\/c\/d"[^>]*>c\/d<\/a> for more\./,
    );
  });

  it("converts a wikilink inside a list item", () => {
    const html = render("- before [[a/b]] after", ["a/b"]);
    expect(html).toMatch(
      /<li>before <a[^>]*href="\/wiki\/a\/b"[^>]*>a\/b<\/a> after<\/li>/,
    );
  });

  it("converts a wikilink inside emphasis", () => {
    const html = render("*see [[a/b]]*", ["a/b"]);
    expect(html).toMatch(
      /<em>see <a[^>]*href="\/wiki\/a\/b"[^>]*>a\/b<\/a><\/em>/,
    );
  });

  it("still renders GFM tables as <table>", () => {
    const html = render(
      "| h1 | h2 |\n| --- | --- |\n| c1 | c2 |",
      [],
    );
    expect(html).toContain("<table>");
    expect(html).toContain("<th>h1</th>");
    expect(html).toContain("<td>c1</td>");
  });
});
