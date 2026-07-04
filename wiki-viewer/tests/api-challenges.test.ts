// Tests for the read-only challenge API routes: list payload never leaks
// solutions; health reports roots.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeAll, afterAll, describe, expect, it } from "vitest";

let fixtureDir: string;
let listRoute: typeof import("@/app/api/challenges/route");
let healthRoute: typeof import("@/app/api/health/route");

beforeAll(async () => {
  fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), "api-challenges-test-"));
  fs.writeFileSync(
    path.join(fixtureDir, "envs.json"),
    JSON.stringify({ runner: { type: "inline", command: ["node", "{file}"], ext: ".mjs" } }),
  );
  fs.mkdirSync(path.join(fixtureDir, "git"));
  fs.writeFileSync(
    path.join(fixtureDir, "git", "rebase-onto.md"),
    [
      "---",
      "wiki: git/rebase",
      "section: Moving Commits",
      "kind: write-code",
      "env: runner",
      "questions:",
      "- Why?",
      "created: 2026-07-03",
      "---",
      "",
      "## Brief",
      "",
      "x",
      "",
      "## Stub",
      "",
      "```js",
      "// TODO",
      "```",
      "",
      "## Solution",
      "",
      "```js",
      "console.log('secret-solution')",
      "```",
      "",
    ].join("\n"),
  );

  process.env.CHALLENGES_ROOT = fixtureDir;
  listRoute = await import("@/app/api/challenges/route");
  healthRoute = await import("@/app/api/health/route");
});

afterAll(() => {
  fs.rmSync(fixtureDir, { recursive: true, force: true });
});

describe("GET /api/challenges", () => {
  it("returns metas only — no solution text anywhere", async () => {
    const res = await listRoute.GET();
    const text = await res.text();
    expect(text).toContain("git/rebase-onto");
    expect(text).toContain('"envType":"inline"');
    expect(text).not.toContain("secret-solution");
  });

  it("is force-dynamic", () => {
    expect(listRoute.dynamic).toBe("force-dynamic");
  });
});

describe("GET /api/health", () => {
  it("reports ok and the configured roots", async () => {
    const res = await healthRoute.GET();
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.challengesRoot).toBe(fixtureDir);
    expect(typeof data.wikiRoot).toBe("string");
  });
});
