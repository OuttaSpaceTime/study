import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { WikiIndexPayload } from "@/lib/types";

// The route imports lib/wiki, which snapshots process.env.WIKI_ROOT at module
// load. So: build the fixture, set the env var, THEN dynamically import the
// route. No top-level import of the route or lib/wiki anywhere in this file
// (type-only imports are fine; they are erased).

let tmpRoot: string | undefined;
let originalWikiRoot: string | undefined;
let route: typeof import("@/app/api/index/route");
let status: number;
let contentType: string | null;
let body: WikiIndexPayload;

function writePage(rel: string, content: string): void {
  if (!tmpRoot) throw new Error("tmpRoot not initialized");
  const file = path.join(tmpRoot, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, "utf8");
}

beforeAll(async () => {
  tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "wiki-viewer-api-index-"));

  writePage(
    "rails/foreign-keys.md",
    [
      "---",
      "title: Foreign Keys",
      "aliases: [fk]",
      "tags: [rails, db]",
      "created: 2026-01-01",
      "updated: 2026-01-02",
      "flashcard_ids: [cmne7xz9202lx0msonsbfhp3j]",
      "---",
      "",
      "See [[rails/rails-index]] and the bare-slug link [[hsts]].",
      "",
    ].join("\n"),
  );
  writePage(
    "rails/rails-index.md",
    [
      "---",
      "title: Rails Index",
      "aliases: []",
      "tags: [rails]",
      "created: 2026-01-01",
      "updated: 2026-01-01",
      "---",
      "",
      "- [[rails/foreign-keys]]",
      "",
    ].join("\n"),
  );
  writePage(
    "security/hsts.md",
    [
      "---",
      "title: HSTS",
      "aliases: []",
      "tags: [security]",
      "created: 2026-02-01",
      "updated: 2026-02-01",
      "---",
      "",
      "No links here.",
      "",
    ].join("\n"),
  );
  // Both of these must be invisible to the index:
  writePage("indexes/search-index.md", "# not a wiki page\n");
  writePage(".hidden.md", "# dotfile, skipped\n");

  originalWikiRoot = process.env.WIKI_ROOT;
  process.env.WIKI_ROOT = tmpRoot;
  route = await import("@/app/api/index/route");

  const res = await route.GET();
  status = res.status;
  contentType = res.headers.get("content-type");
  body = (await res.json()) as WikiIndexPayload;
});

afterAll(() => {
  if (originalWikiRoot === undefined) delete process.env.WIKI_ROOT;
  else process.env.WIKI_ROOT = originalWikiRoot;
  if (tmpRoot) fs.rmSync(tmpRoot, { recursive: true, force: true });
});

describe("GET /api/index", () => {
  it("is exported as force-dynamic", () => {
    expect(route.dynamic).toBe("force-dynamic");
  });

  it("responds 200 with JSON", () => {
    expect(status).toBe(200);
    expect(contentType).toContain("application/json");
  });

  it("returns the fixture pages sorted by path, an *-index page among them", () => {
    expect(body.pages.map((p) => p.path)).toEqual([
      "rails/foreign-keys",
      "rails/rails-index",
      "security/hsts",
    ]);
  });

  it("maps frontmatter onto PageMeta for a known page", () => {
    const page = body.pages.find((p) => p.path === "rails/foreign-keys");
    expect(page).toBeDefined();
    if (!page) return;
    expect(page.title).toBe("Foreign Keys");
    expect(page.folder).toBe("rails");
    expect(page.slug).toBe("foreign-keys");
    expect(page.aliases).toEqual(["fk"]);
    expect(page.tags).toEqual(["rails", "db"]);
    expect(page.created).toBe("2026-01-01");
    expect(page.flashcardIds).toEqual(["cmne7xz9202lx0msonsbfhp3j"]);
  });

  it("resolves outbound links (bare-slug fallback) both ways", () => {
    const page = body.pages.find((p) => p.path === "rails/foreign-keys");
    expect(page?.outbound).toEqual(["rails/rails-index", "security/hsts"]);
    expect(page?.inbound).toEqual(["rails/rails-index"]);
  });

  it("builds the folder tree from the fixture", () => {
    expect(body.tree.name).toBe("wiki");
    expect(body.tree.path).toBe("");
    expect(body.tree.pages).toEqual([]);
    expect(body.tree.folders.map((f) => f.name)).toEqual(["rails", "security"]);
    const rails = body.tree.folders.find((f) => f.name === "rails");
    expect(rails?.path).toBe("rails");
    expect(rails?.pages.map((p) => p.slug)).toEqual(["foreign-keys", "rails-index"]);
  });

  it("builds the graph with one node per page, links deduped", () => {
    expect(body.graph.nodes.map((n) => n.id).sort()).toEqual([
      "rails/foreign-keys",
      "rails/rails-index",
      "security/hsts",
    ]);
    const fk = body.graph.nodes.find((n) => n.id === "rails/foreign-keys");
    // 2 outbound + 1 inbound
    expect(fk?.linkCount).toBe(3);
    // foreign-keys<->rails-index collapses to one link; foreign-keys->hsts is the other.
    expect(body.graph.links).toHaveLength(2);
    const pairs = body.graph.links.map((l) => [l.source, l.target].sort().join("→")).sort();
    expect(pairs).toEqual([
      "rails/foreign-keys→rails/rails-index",
      "rails/foreign-keys→security/hsts",
    ]);
  });

  it("stamps generatedAt with a parseable ISO timestamp", () => {
    expect(typeof body.generatedAt).toBe("string");
    expect(Number.isNaN(Date.parse(body.generatedAt))).toBe(false);
  });
});
