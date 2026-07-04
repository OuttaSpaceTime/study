// Regression: a trailing slash on the WIKI_ROOT env var must not break the
// safeWikiFile traversal guard (`startsWith(WIKI_ROOT + path.sep)`), which
// would make every page lookup return null. Lives in its own file because
// WIKI_ROOT is snapshotted at module load.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

let fixtureDir: string;
let wiki: typeof import("@/lib/wiki");

beforeAll(async () => {
  fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), "wiki-root-norm-"));
  fs.mkdirSync(path.join(fixtureDir, "a"));
  fs.writeFileSync(
    path.join(fixtureDir, "a", "page.md"),
    "---\ntitle: Page\n---\n\n# Page\n\nBody.\n",
  );
  process.env.WIKI_ROOT = fixtureDir + path.sep; // note the trailing slash
  wiki = await import("@/lib/wiki");
});

afterAll(() => {
  delete process.env.WIKI_ROOT;
  fs.rmSync(fixtureDir, { recursive: true, force: true });
});

describe("WIKI_ROOT normalization", () => {
  it("strips the trailing slash from the env var", () => {
    expect(wiki.WIKI_ROOT).toBe(fixtureDir);
  });

  it("safeWikiFile still accepts valid pages", () => {
    expect(wiki.safeWikiFile("a/page")).toBe(
      path.join(fixtureDir, "a", "page.md"),
    );
  });

  it("safeWikiFile still rejects traversal", () => {
    expect(wiki.safeWikiFile("../escape")).toBeNull();
  });

  it("getPage finds the page", async () => {
    const page = await wiki.getPage("a/page");
    expect(page?.meta.title).toBe("Page");
  });
});
