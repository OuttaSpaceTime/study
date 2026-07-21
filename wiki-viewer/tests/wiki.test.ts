// Tests for the server data layer lib/wiki.ts.
//
// lib/wiki.ts reads WIKI_ROOT from process.env at module load, so the fixture
// wiki is built and the env var set BEFORE the module is dynamically imported
// in beforeAll. All assertions run against one index snapshot taken there;
// fixture files are never mutated mid-suite.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { PageMeta, TreeFolder, WikiIndexPayload } from "@/lib/types";

type WikiModule = typeof import("@/lib/wiki");

const FENCE = "```";

/** Page paths the payload should yield (MOC *-index pages are excluded —
 * they survive only as ghost nodes in the graph), in localeCompare order. */
const EXPECTED_PATHS = [
  "a/dupe",
  "b/dupe",
  "code-fenced-target",
  "embed-only",
  "inline-code-target",
  "linker",
  "no-study/secret",
  "rails/alpha-page",
  "rails/routing/scope-vs-namespace",
  "rails/zeta-topic",
  "tools/unique-slug",
];
const MOC_PATH = "rails/rails-index";

let fixtureDir: string;
let wiki: WikiModule;
let index: WikiIndexPayload;

function writeFixture(rel: string, content: string): void {
  const file = path.join(fixtureDir, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function mustPage(pagePath: string): PageMeta {
  const page = index.pages.find((p) => p.path === pagePath);
  if (!page) throw new Error(`fixture page not in index: ${pagePath}`);
  return page;
}

function mustFolder(parent: TreeFolder, name: string): TreeFolder {
  const folder = parent.folders.find((f) => f.name === name);
  if (!folder) throw new Error(`folder "${name}" not under "${parent.path}"`);
  return folder;
}

beforeAll(async () => {
  fixtureDir = fs.realpathSync(
    fs.mkdtempSync(path.join(os.tmpdir(), "wiki-viewer-test-")),
  );

  // Page exercising every link form. Unquoted created/next_review become
  // Date objects in gray-matter; updated is quoted and stays a string.
  writeFixture(
    "linker.md",
    [
      "---",
      "title: Linker Page",
      "aliases:",
      "  - linkz",
      "  - the-linker",
      "tags:",
      "  - testing",
      "  - links",
      "created: 2026-01-05",
      'updated: "2026-02-03"',
      "next_review: 2026-03-15",
      "review_interval: 5",
      "depth: 2",
      "---",
      "Absolute: [[rails/routing/scope-vs-namespace]]",
      "Pipe: [[rails/rails-index|Rails MOC]]",
      "Anchor: [[rails/routing/scope-vs-namespace#Scope]]",
      "Slug fallback: [[unique-slug]]",
      "Ambiguous: [[dupe]]",
      "Broken: [[nowhere/missing]]",
      "Self: [[linker]]",
      "Embed: ![[embed-only]]",
      "",
      "Inline code: `[[inline-code-target]]`",
      "",
      `${FENCE}text`,
      "[[code-fenced-target]]",
      FENCE,
      "",
      "Body ends here.",
    ].join("\n"),
  );

  // MOC index page; no created/updated/next_review (missing optional fields).
  writeFixture(
    "rails/rails-index.md",
    ["---", "title: Rails Index", "tags:", "  - moc", "---", "- [[rails/alpha-page]]"].join(
      "\n",
    ),
  );
  writeFixture(
    "rails/alpha-page.md",
    [
      "---",
      "title: Alpha Page",
      "---",
      "Alpha body.",
      "",
      "## First Section",
      "",
      "Text.",
      "",
      `${FENCE}text`,
      "## Not A Heading",
      FENCE,
      "",
      "## Second Section",
      "",
      "More.",
    ].join("\n"),
  );
  writeFixture(
    "rails/zeta-topic.md",
    ["---", "title: Zeta Topic", "---", "Zeta body."].join("\n"),
  );
  // 2-level nested page that links back to linker (mutual pair for graph dedupe).
  writeFixture(
    "rails/routing/scope-vs-namespace.md",
    [
      "---",
      "title: Scope vs Namespace",
      "created: 2026-04-01",
      "---",
      "## Scope",
      "",
      "Back to [[linker]].",
    ].join("\n"),
  );

  // Two pages sharing the slug "dupe" — bare [[dupe]] must stay unresolved.
  writeFixture("a/dupe.md", ["---", "title: Dupe A", "---", "A."].join("\n"));
  writeFixture("b/dupe.md", ["---", "title: Dupe B", "---", "B."].join("\n"));

  // No frontmatter at all: title falls back to slug, optionals default.
  writeFixture("tools/unique-slug.md", "Unique body.\n");

  // Link targets that must receive NO inbound links.
  writeFixture("embed-only.md", "Embed target body.\n");
  writeFixture("code-fenced-target.md", "Fenced target body.\n");
  writeFixture("inline-code-target.md", "Inline target body.\n");

  // No-study page: full wiki member, only excluded from the study loop.
  writeFixture(
    "no-study/secret.md",
    ["---", "title: Secret Note", "tags:", "  - no-study", "---", "No-study body."].join(
      "\n",
    ),
  );

  // Content that must be skipped by discovery.
  writeFixture("indexes/skipme.md", "Should never be indexed.\n");
  writeFixture(".obsidian/hidden.md", "Dotfolder page, skipped.\n");
  writeFixture(".hidden-root.md", "Dotfile, skipped.\n");
  writeFixture("notes.txt", "Not markdown.\n");

  process.env.WIKI_ROOT = fixtureDir;
  wiki = await import("@/lib/wiki");
  index = await wiki.getWikiIndex();
});

afterAll(() => {
  fs.rmSync(fixtureDir, { recursive: true, force: true });
  delete process.env.WIKI_ROOT;
});

describe("page discovery", () => {
  it("uses the fixture dir as WIKI_ROOT (hermeticity guard)", () => {
    expect(wiki.WIKI_ROOT).toBe(fixtureDir);
  });

  it("finds all .md pages sorted by path, skipping indexes/, dotfolders, dotfiles, and non-md files", () => {
    expect(index.pages.map((p) => p.path)).toEqual(EXPECTED_PATHS);
  });
});

describe("page meta", () => {
  it('normalizes unquoted YAML dates (Date objects) to "YYYY-MM-DD" strings', () => {
    const linker = mustPage("linker");
    expect(linker.created).toBe("2026-01-05");
    expect(linker.nextReview).toBe("2026-03-15");
    expect(mustPage("rails/routing/scope-vs-namespace").created).toBe("2026-04-01");
  });

  it("passes through quoted date strings and parses arrays/numbers", () => {
    const linker = mustPage("linker");
    expect(linker.updated).toBe("2026-02-03");
    expect(linker.title).toBe("Linker Page");
    expect(linker.aliases).toEqual(["linkz", "the-linker"]);
    expect(linker.tags).toEqual(["testing", "links"]);
    expect(linker.reviewInterval).toBe(5);
    expect(linker.depth).toBe(2);
  });

  it("falls back to slug for title and defaults optionals when frontmatter is missing", () => {
    const page = mustPage("tools/unique-slug");
    expect(page.title).toBe("unique-slug");
    expect(page.aliases).toEqual([]);
    expect(page.tags).toEqual([]);
    expect(page.created).toBe("");
    expect(page.updated).toBe("");
    expect(page.nextReview).toBe("");
    expect(page.reviewInterval).toBeNull();
    expect(page.depth).toBeNull();
    expect(page.isIndex).toBe(false);
  });

  it("extracts H2 headings in order, skipping those inside fenced code blocks", () => {
    expect(mustPage("rails/alpha-page").sections).toEqual([
      "First Section",
      "Second Section",
    ]);
    expect(mustPage("rails/routing/scope-vs-namespace").sections).toEqual(["Scope"]);
    expect(mustPage("tools/unique-slug").sections).toEqual([]);
  });

  it("splits path into folder and slug for top-level and nested pages", () => {
    const linker = mustPage("linker");
    expect(linker.folder).toBe("");
    expect(linker.slug).toBe("linker");
    const nested = mustPage("rails/routing/scope-vs-namespace");
    expect(nested.folder).toBe("rails/routing");
    expect(nested.slug).toBe("scope-vs-namespace");
  });

  it("excludes *-index MOC pages from the page list; they exist only as graph ghosts", () => {
    expect(index.pages.some((p) => p.path === MOC_PATH)).toBe(false);
    const ghost = index.graph.nodes.find((n) => n.id === MOC_PATH);
    if (!ghost) throw new Error("MOC ghost node missing from graph");
    expect(ghost.isIndex).toBe(true);
    expect(ghost.folder).toBe("rails");
    expect(mustPage("linker").isIndex).toBe(false);
  });
});

describe("no-study pages", () => {
  it("keeps a no-study-tagged page in the page list, tree, and graph, still flagged no-study", () => {
    expect(index.pages.some((p) => p.path === "no-study/secret")).toBe(true);
    expect(index.tree.folders.some((f) => f.name === "no-study")).toBe(true);
    expect(index.graph.nodes.some((n) => n.id === "no-study/secret")).toBe(true);
    expect(mustPage("no-study/secret").tags).toContain("no-study");
  });
});

describe("link resolution", () => {
  it("resolves linker outbound: exact + pipe + anchor (deduped) + unique-slug fallback, sorted", () => {
    // Absolute and anchor forms of scope-vs-namespace collapse to one entry;
    // ambiguous [[dupe]], broken [[nowhere/missing]], self [[linker]],
    // embed ![[embed-only]], and code-wrapped links are all excluded. The
    // [[rails/rails-index]] MOC link is stripped from page meta (graph-only).
    expect(mustPage("linker").outbound).toEqual([
      "rails/routing/scope-vs-namespace",
      "tools/unique-slug",
    ]);
  });

  it("does not resolve an ambiguous bare slug", () => {
    expect(mustPage("a/dupe").inbound).toEqual([]);
    expect(mustPage("b/dupe").inbound).toEqual([]);
  });

  it("ignores wikilinks inside fenced code blocks and inline code", () => {
    expect(mustPage("code-fenced-target").inbound).toEqual([]);
    expect(mustPage("inline-code-target").inbound).toEqual([]);
    expect(mustPage("linker").outbound).not.toContain("code-fenced-target");
    expect(mustPage("linker").outbound).not.toContain("inline-code-target");
  });

  it("ignores embeds", () => {
    expect(mustPage("embed-only").inbound).toEqual([]);
    expect(mustPage("linker").outbound).not.toContain("embed-only");
  });

  it("resolves an exact absolute link from a nested page back to the top level", () => {
    expect(mustPage("rails/routing/scope-vs-namespace").outbound).toEqual(["linker"]);
    expect(mustPage("linker").inbound).toEqual(["rails/routing/scope-vs-namespace"]);
  });

  it("keeps inbound and outbound symmetric, both sorted", () => {
    for (const page of index.pages) {
      for (const target of page.outbound) {
        expect(mustPage(target).inbound).toContain(page.path);
      }
      for (const source of page.inbound) {
        expect(mustPage(source).outbound).toContain(page.path);
      }
      expect([...page.outbound].sort()).toEqual(page.outbound);
      expect([...page.inbound].sort()).toEqual(page.inbound);
    }
  });
});

describe("tree", () => {
  it('has root named "wiki" with empty path and folders sorted by name', () => {
    expect(index.tree.name).toBe("wiki");
    expect(index.tree.path).toBe("");
    expect(index.tree.folders.map((f) => f.name)).toEqual(["a", "b", "no-study", "rails", "tools"]);
  });

  it("excludes the MOC from the tree and orders pages by title", () => {
    const rails = mustFolder(index.tree, "rails");
    expect(rails.pages.map((p) => p.path)).toEqual([
      "rails/alpha-page",
      "rails/zeta-topic",
    ]);
  });

  it("reaches the 2-level nested folder with its page", () => {
    const routing = mustFolder(mustFolder(index.tree, "rails"), "routing");
    expect(routing.path).toBe("rails/routing");
    expect(routing.pages.map((p) => p.path)).toEqual([
      "rails/routing/scope-vs-namespace",
    ]);
    expect(routing.folders).toEqual([]);
  });

  it("places top-level pages directly in the root folder", () => {
    expect(index.tree.pages.map((p) => p.path).sort()).toEqual([
      "code-fenced-target",
      "embed-only",
      "inline-code-target",
      "linker",
    ]);
  });
});

describe("graph", () => {
  it("has one node per page plus the MOC ghost", () => {
    expect(index.graph.nodes).toHaveLength(EXPECTED_PATHS.length + 1);
    expect(index.graph.nodes.map((n) => n.id).sort()).toEqual(
      [...EXPECTED_PATHS, MOC_PATH].sort(),
    );
  });

  it("sets linkCount to full degree including MOC edges (pre-strip)", () => {
    const degree = (id: string) => {
      const node = index.graph.nodes.find((n) => n.id === id);
      if (!node) throw new Error(`node missing: ${id}`);
      return node.linkCount;
    };
    // linker keeps its MOC edge in the graph (3 outbound + 1 inbound) even
    // though page meta now lists only 2 outbound.
    expect(degree("linker")).toBe(4);
    expect(mustPage("linker").outbound).toHaveLength(2);
    // alpha-page's only edge is from the MOC ghost; page meta shows none.
    expect(degree("rails/alpha-page")).toBe(1);
    expect(mustPage("rails/alpha-page").inbound).toEqual([]);
    // The ghost itself: outbound to alpha-page + inbound from linker.
    expect(degree(MOC_PATH)).toBe(2);
  });

  it("dedupes undirected links: a mutual A→B / B→A pair yields one link", () => {
    const between = index.graph.links.filter(
      (l) =>
        (l.source === "linker" && l.target === "rails/routing/scope-vs-namespace") ||
        (l.source === "rails/routing/scope-vs-namespace" && l.target === "linker"),
    );
    expect(between).toHaveLength(1);
    // linker→{rails-index, scope-vs-namespace, unique-slug} + rails-index→alpha-page
    expect(index.graph.links).toHaveLength(4);
  });
});

describe("safeWikiFile", () => {
  it("rejects parent-dir escapes", () => {
    expect(wiki.safeWikiFile("../escape")).toBeNull();
    expect(wiki.safeWikiFile("a/../../escape")).toBeNull();
  });

  it("rejects absolute path tricks", () => {
    expect(wiki.safeWikiFile("/etc/passwd")).toBeNull();
    expect(wiki.safeWikiFile(path.join(os.tmpdir(), "outside"))).toBeNull();
  });

  it("resolves a valid wiki path to a file under the root", () => {
    expect(wiki.safeWikiFile("rails/rails-index")).toBe(
      path.join(fixtureDir, "rails", "rails-index.md"),
    );
    expect(wiki.safeWikiFile("linker")).toBe(path.join(fixtureDir, "linker.md"));
  });
});

describe("getPage", () => {
  it("returns meta and frontmatter-stripped, trimmed markdown for an existing page", async () => {
    const page = await wiki.getPage("linker");
    if (!page) throw new Error("expected linker page");
    expect(page.meta.path).toBe("linker");
    expect(page.meta.title).toBe("Linker Page");
    expect(page.markdown.startsWith("Absolute:")).toBe(true);
    expect(page.markdown.endsWith("Body ends here.")).toBe(true);
    expect(page.markdown).not.toContain("title: Linker Page");
    expect(page.markdown).not.toContain("---\ntitle");
  });

  it("returns null for a missing page", async () => {
    expect(await wiki.getPage("rails/does-not-exist")).toBeNull();
  });

  it("returns null for a path escaping the root", async () => {
    expect(await wiki.getPage("../linker")).toBeNull();
  });
});

describe("index cache", () => {
  it("returns the identical snapshot for two calls within the TTL", async () => {
    const first = wiki.getWikiIndex();
    const second = wiki.getWikiIndex();
    expect(second).toBe(first); // same cached promise
    expect(await second).toBe(await first); // same resolved payload object
  });
});
