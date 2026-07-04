// Tests for the challenge data layer lib/challenges.ts.
//
// lib/challenges.ts reads CHALLENGES_ROOT from process.env at module load, so
// the fixture dir is built and the env var set BEFORE the dynamic import in
// beforeAll (same pattern as wiki.test.ts).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { normalizeSection } from "@/lib/challenge-types";

type ChallengesModule = typeof import("@/lib/challenges");

const FENCE = "```";

let fixtureDir: string;
let mod: ChallengesModule;

function writeFixture(rel: string, content: string): void {
  const file = path.join(fixtureDir, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function challengeDoc(opts: {
  wiki?: string;
  section?: string;
  kind?: string;
  env?: string;
  questions?: string[];
  stubLang?: string;
  stubCode?: string;
  solutionCode?: string;
  expected?: string;
}): string {
  const lines = ["---"];
  if (opts.wiki) lines.push(`wiki: ${JSON.stringify(opts.wiki)}`);
  if (opts.section) lines.push(`section: ${JSON.stringify(opts.section)}`);
  lines.push(`kind: ${opts.kind ?? "write-code"}`);
  lines.push(`env: ${opts.env ?? "nodetest"}`);
  const questions = opts.questions ?? ["Why?"];
  if (questions.length) {
    lines.push("questions:");
    for (const q of questions) lines.push(`- ${q}`);
  }
  lines.push("created: 2026-07-03");
  lines.push("---");
  lines.push("");
  lines.push("## Brief");
  lines.push("");
  lines.push("Do the thing.");
  lines.push("");
  lines.push("## Stub");
  lines.push("");
  lines.push(`${FENCE}${opts.stubLang ?? "js"}`);
  lines.push(opts.stubCode ?? "// TODO");
  lines.push(FENCE);
  lines.push("");
  lines.push("## Solution");
  lines.push("");
  lines.push(`${FENCE}${opts.stubLang ?? "js"}`);
  lines.push(opts.solutionCode ?? 'console.log("secret-solution")');
  lines.push(FENCE);
  if (opts.expected !== undefined) {
    lines.push("");
    lines.push("## Expected Output");
    lines.push("");
    lines.push(FENCE);
    lines.push(opts.expected);
    lines.push(FENCE);
  }
  lines.push("");
  return lines.join("\n");
}

beforeAll(async () => {
  fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), "challenges-test-"));
  writeFixture(
    "envs.json",
    JSON.stringify({
      nodetest: { type: "inline", command: ["node", "{file}"], ext: ".mjs" },
      webtest: { type: "browser" },
    }),
  );
  writeFixture("security/hsts-preload.md", challengeDoc({
    wiki: "security/hsts",
    section: "Preload",
    expected: "done",
  }));
  writeFixture("security/fence-trap.md", challengeDoc({
    wiki: "security/hsts",
    section: "Browser Storage",
    stubCode: "// not a heading:\n// ## Solution inside a fence\nlet x = 1",
  }));
  writeFixture("scratch/2026-07-03-1430-closures.md", challengeDoc({}));
  writeFixture("security/_draft.md", challengeDoc({ wiki: "security/hsts", section: "Draft" }));
  writeFixture("_template.md", challengeDoc({ wiki: "x/y", section: "Z" }));
  writeFixture("README.md", "# Challenges\n");
  writeFixture(".attempts/security/hsts-preload.json", "{}");
  writeFixture("envs/rails-play/NOTES.md", challengeDoc({ wiki: "a/b", section: "C" }));
  writeFixture("security/dupe-a.md", challengeDoc({ wiki: "git/rebase", section: "Same Spot" }));
  writeFixture("security/dupe-b.md", challengeDoc({ wiki: "git/rebase", section: "same spot:" }));

  process.env.CHALLENGES_ROOT = fixtureDir;
  mod = await import("@/lib/challenges");
});

afterAll(() => {
  fs.rmSync(fixtureDir, { recursive: true, force: true });
});

describe("normalizeSection", () => {
  it("lowercases, trims, strips trailing punctuation like the Python linter", () => {
    expect(normalizeSection("  Preload Pitfalls?  ")).toBe("preload pitfalls");
    expect(normalizeSection("The Header Fields:")).toBe("the header fields");
    expect(normalizeSection("Plain")).toBe("plain");
  });
});

describe("getChallengeIndex", () => {
  it("discovers challenges with parsed metas", async () => {
    const index = await mod.getChallengeIndex();
    const ids = index.challenges.map((c) => c.id);
    expect(ids).toContain("security/hsts-preload");
    expect(ids).toContain("scratch/2026-07-03-1430-closures");
  });

  it("skips _-prefixed, template, readme, .attempts and envs dirs", async () => {
    const index = await mod.getChallengeIndex();
    const ids = index.challenges.map((c) => c.id);
    expect(ids).not.toContain("security/_draft");
    expect(ids.some((id) => id.includes("_template"))).toBe(false);
    expect(ids.some((id) => id.includes("README"))).toBe(false);
    expect(ids.some((id) => id.startsWith("envs/"))).toBe(false);
    expect(ids.some((id) => id.includes(".attempts"))).toBe(false);
  });

  it("maps frontmatter onto meta including envType", async () => {
    const index = await mod.getChallengeIndex();
    const c = index.challenges.find((x) => x.id === "security/hsts-preload");
    expect(c).toBeDefined();
    expect(c!.wiki).toBe("security/hsts");
    expect(c!.section).toBe("Preload");
    expect(c!.sectionNorm).toBe("preload");
    expect(c!.kind).toBe("write-code");
    expect(c!.env).toBe("nodetest");
    expect(c!.envType).toBe("inline");
    expect(c!.questions).toEqual(["Why?"]);
    expect(c!.created).toBe("2026-07-03");
  });

  it("marks scratch challenges and leaves wiki/section null", async () => {
    const index = await mod.getChallengeIndex();
    const c = index.challenges.find((x) => x.id === "scratch/2026-07-03-1430-closures");
    expect(c!.wiki).toBeNull();
    expect(c!.sectionNorm).toBeNull();
  });

  it("dedupes (wiki, sectionNorm) collisions keeping the lexicographically first id", async () => {
    const index = await mod.getChallengeIndex();
    const same = index.challenges.filter(
      (c) => c.wiki === "git/rebase" && c.sectionNorm === "same spot",
    );
    expect(same.map((c) => c.id)).toEqual(["security/dupe-a"]);
  });

  it("returns the same promise within the cache TTL", () => {
    expect(mod.getChallengeIndex()).toBe(mod.getChallengeIndex());
  });
});

describe("safeChallengeId", () => {
  it("accepts two well-formed segments", () => {
    expect(mod.safeChallengeId("security/hsts-preload")).toEqual({
      topic: "security",
      slug: "hsts-preload",
    });
  });

  it("rejects traversal, wrong arity and hostile segments", () => {
    expect(mod.safeChallengeId("../../etc/passwd")).toBeNull();
    expect(mod.safeChallengeId("security/../../x")).toBeNull();
    expect(mod.safeChallengeId("security")).toBeNull();
    expect(mod.safeChallengeId("a/b/c")).toBeNull();
    expect(mod.safeChallengeId("/abs/path")).toBeNull();
    expect(mod.safeChallengeId("se curity/x")).toBeNull();
    expect(mod.safeChallengeId(".hidden/x")).toBeNull();
    expect(mod.safeChallengeId("")).toBeNull();
  });
});

describe("getChallenge", () => {
  it("splits body sections and extracts code blocks", async () => {
    const detail = await mod.getChallenge("security/hsts-preload");
    expect(detail).not.toBeNull();
    expect(detail!.brief).toContain("Do the thing");
    expect(detail!.stub).toEqual([{ lang: "js", code: "// TODO" }]);
    expect(detail!.solution).toEqual([
      { lang: "js", code: 'console.log("secret-solution")' },
    ]);
    expect(detail!.expectedOutput).toBe("done");
  });

  it("does not treat '## ' inside a code fence as a section boundary", async () => {
    const detail = await mod.getChallenge("security/fence-trap");
    expect(detail!.stub).toHaveLength(1);
    expect(detail!.stub[0]!.code).toContain("## Solution inside a fence");
    expect(detail!.solution).toEqual([
      { lang: "js", code: 'console.log("secret-solution")' },
    ]);
  });

  it("returns null for unknown or malformed ids", async () => {
    expect(await mod.getChallenge("security/nope")).toBeNull();
    expect(await mod.getChallenge("../../etc/passwd")).toBeNull();
  });
});

describe("toStudyPayload", () => {
  it("never contains the solution", async () => {
    const detail = await mod.getChallenge("security/hsts-preload");
    const payload = mod.toStudyPayload(detail!);
    expect(JSON.stringify(payload)).not.toContain("secret-solution");
    expect(payload.stub).toEqual([{ lang: "js", code: "// TODO" }]);
  });

  it("keeps expectedOutput for write-code and strips it for predict-output", async () => {
    const detail = await mod.getChallenge("security/hsts-preload");
    expect(mod.toStudyPayload(detail!).expectedOutput).toBe("done");
    const predict = {
      ...detail!,
      meta: { ...detail!.meta, kind: "predict-output" as const },
    };
    expect(mod.toStudyPayload(predict).expectedOutput).toBeNull();
  });
});

describe("getEnvRegistry", () => {
  it("returns validated entries", async () => {
    const envs = await mod.getEnvRegistry();
    expect(envs.nodetest).toEqual({
      type: "inline",
      command: ["node", "{file}"],
      ext: ".mjs",
    });
    expect(envs.webtest!.type).toBe("browser");
  });
});

describe("attempts", () => {
  it("writes and reads an attempt under .attempts/<topic>/<slug>.json", async () => {
    const record = {
      id: "security/hsts-preload",
      kind: "write-code" as const,
      env: "nodetest",
      code: "console.log(1)",
      output: "1",
      exitCode: 0,
      timedOut: false,
      status: "ran" as const,
      runCount: 1,
      updatedAt: "2026-07-03T12:00:00.000Z",
    };
    await mod.writeAttempt("security/hsts-preload", record);
    const file = path.join(fixtureDir, ".attempts", "security", "hsts-preload.json");
    expect(fs.existsSync(file)).toBe(true);
    expect(await mod.readAttempt("security/hsts-preload")).toEqual(record);
  });

  it("returns null for missing attempts and rejects bad ids", async () => {
    expect(await mod.readAttempt("security/never-attempted")).toBeNull();
    expect(await mod.readAttempt("../../etc/passwd")).toBeNull();
  });
});
