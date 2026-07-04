// Tests for the run/attempt API routes — execution, status computation,
// attempt persistence, and the security gate. Uses process.execPath as the
// pinned interpreter so no PATH assumptions leak in.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { beforeAll, afterAll, describe, expect, it } from "vitest";

type RunRoute = typeof import("@/app/api/challenges/[topic]/[slug]/run/route");
type AttemptRoute = typeof import("@/app/api/challenges/[topic]/[slug]/attempt/route");
type SecurityModule = typeof import("@/lib/security");

const FENCE = "```";

let fixtureDir: string;
let runRoute: RunRoute;
let attemptRoute: AttemptRoute;
let security: SecurityModule;

function writeFixture(rel: string, content: string): void {
  const file = path.join(fixtureDir, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

function challengeDoc(opts: {
  kind?: string;
  env?: string;
  stubCode?: string;
  solutionCode?: string;
  expected?: string;
}): string {
  const lines = [
    "---",
    "wiki: security/hsts",
    "section: Preload",
    `kind: ${opts.kind ?? "write-code"}`,
    `env: ${opts.env ?? "runner"}`,
    "questions:",
    "- Why?",
    "created: 2026-07-03",
    "---",
    "",
    "## Brief",
    "",
    "Run it.",
    "",
    "## Stub",
    "",
    `${FENCE}js`,
    opts.stubCode ?? "// TODO",
    FENCE,
    "",
    "## Solution",
    "",
    `${FENCE}js`,
    opts.solutionCode ?? "console.log('solved')",
    FENCE,
  ];
  if (opts.expected !== undefined) {
    lines.push("", "## Expected Output", "", FENCE, opts.expected, FENCE);
  }
  lines.push("");
  return lines.join("\n");
}

function post(
  id: string,
  body: unknown,
  headers?: Record<string, string>,
): [Request, { params: Promise<{ topic: string; slug: string }> }] {
  const [topic = "", slug = ""] = id.split("/");
  const req = new Request(`http://localhost:3000/api/challenges/${id}/run`, {
    method: "POST",
    headers: headers ?? {
      host: "localhost:3000",
      "content-type": "application/json",
      "x-study-csrf": security.CSRF_TOKEN,
    },
    body: JSON.stringify(body),
  });
  return [req, { params: Promise.resolve({ topic, slug }) }];
}

beforeAll(async () => {
  fixtureDir = fs.mkdtempSync(path.join(os.tmpdir(), "run-route-test-"));
  writeFixture(
    "envs.json",
    JSON.stringify({
      runner: { type: "inline", command: [process.execPath, "{file}"], ext: ".mjs" },
      slowrunner: {
        type: "inline",
        command: [process.execPath, "{file}"],
        ext: ".mjs",
        timeoutMs: 1000,
      },
      webtest: { type: "browser" },
    }),
  );
  writeFixture("node/echo.md", challengeDoc({ expected: "hello" }));
  writeFixture("node/free.md", challengeDoc({}));
  writeFixture(
    "node/predict.md",
    challengeDoc({ kind: "predict-output", stubCode: "console.log('from-disk-stub')" }),
  );
  writeFixture("node/spin.md", challengeDoc({ env: "slowrunner" }));
  writeFixture("node/browser-kind.md", challengeDoc({ env: "webtest" }));
  writeFixture("node/bad-env.md", challengeDoc({ env: "missing-env" }));
  writeFixture("node/untouched.md", challengeDoc({}));

  process.env.CHALLENGES_ROOT = fixtureDir;
  security = await import("@/lib/security");
  runRoute = await import("@/app/api/challenges/[topic]/[slug]/run/route");
  attemptRoute = await import("@/app/api/challenges/[topic]/[slug]/attempt/route");
});

afterAll(() => {
  fs.rmSync(fixtureDir, { recursive: true, force: true });
});

describe("POST /run", () => {
  it("runs submitted code and persists the attempt", async () => {
    const [req, ctx] = post("node/free", { code: "console.log('hi from test')" });
    const res = await runRoute.POST(req, ctx);
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.output).toContain("hi from test");
    expect(data.exitCode).toBe(0);
    expect(data.status).toBe("ran");
    const attempt = JSON.parse(
      fs.readFileSync(path.join(fixtureDir, ".attempts", "node", "free.json"), "utf8"),
    );
    expect(attempt.code).toBe("console.log('hi from test')");
    expect(attempt.runCount).toBe(1);
  });

  it("marks pass when output matches Expected Output", async () => {
    const [req, ctx] = post("node/echo", { code: "console.log('hello')" });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.status).toBe("pass");
  });

  it("marks differs when output does not match", async () => {
    const [req, ctx] = post("node/echo", { code: "console.log('nope')" });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.status).toBe("differs");
  });

  it("marks error on nonzero exit", async () => {
    const [req, ctx] = post("node/free", { code: "process.exit(3)" });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.exitCode).toBe(3);
    expect(data.status).toBe("error");
  });

  it("kills runaway code at the env timeout", async () => {
    const [req, ctx] = post("node/spin", { code: "for(;;){}" });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.timedOut).toBe(true);
    expect(data.status).toBe("error");
  }, 15_000);

  it("caps runaway output instead of buffering it", async () => {
    const [req, ctx] = post("node/free", {
      code: "for(let i=0;i<100000;i++)console.log('x'.repeat(100))",
    });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.output.length).toBeLessThanOrEqual(64 * 1024);
    expect(data.timedOut).toBe(false);
  });

  it("predict-output runs the stub from disk and ignores request code", async () => {
    const [req, ctx] = post("node/predict", {
      code: "console.log('evil-injected')",
      predictedOutput: "from-disk-stub",
    });
    const data = await (await runRoute.POST(req, ctx)).json();
    expect(data.output).toContain("from-disk-stub");
    expect(data.output).not.toContain("evil-injected");
    expect(data.status).toBe("pass");
  });

  it("increments runCount across runs", async () => {
    const [req1, ctx1] = post("node/echo", { code: "console.log('hello')" });
    const first = await (await runRoute.POST(req1, ctx1)).json();
    const [req2, ctx2] = post("node/echo", { code: "console.log('hello')" });
    const second = await (await runRoute.POST(req2, ctx2)).json();
    expect(second.runCount).toBe(first.runCount + 1);
  });

  it("rejects browser-env challenges with 400", async () => {
    const [req, ctx] = post("node/browser-kind", { code: "1" });
    expect((await runRoute.POST(req, ctx)).status).toBe(400);
  });

  it("returns 500 for an env missing from the registry", async () => {
    const [req, ctx] = post("node/bad-env", { code: "1" });
    expect((await runRoute.POST(req, ctx)).status).toBe(500);
  });

  it("returns 404 for traversal ids and writes nothing", async () => {
    const req = new Request("http://localhost:3000/api/challenges/x/run", {
      method: "POST",
      headers: { host: "localhost:3000", "x-study-csrf": security.CSRF_TOKEN },
      body: JSON.stringify({ code: "1" }),
    });
    const res = await runRoute.POST(req, {
      params: Promise.resolve({ topic: "..", slug: "escape" }),
    });
    expect(res.status).toBe(404);
  });

  it("rejects a request without the CSRF token and writes no attempt", async () => {
    const [req, ctx] = post("node/untouched", { code: "console.log('x')" }, {
      host: "localhost:3000",
      "content-type": "application/json",
    });
    const res = await runRoute.POST(req, ctx);
    expect(res.status).toBe(403);
    expect(
      fs.existsSync(path.join(fixtureDir, ".attempts", "node", "untouched.json")),
    ).toBe(false);
  });
});

describe("POST /attempt", () => {
  it("persists browser-kind attempts", async () => {
    const [topic, slug] = ["node", "browser-kind"];
    const req = new Request(
      `http://localhost:3000/api/challenges/${topic}/${slug}/attempt`,
      {
        method: "POST",
        headers: { host: "localhost:3000", "x-study-csrf": security.CSRF_TOKEN },
        body: JSON.stringify({
          files: [{ lang: "js", code: "console.log('render me')" }],
          output: "render me",
          status: "ran",
        }),
      },
    );
    const res = await attemptRoute.POST(req, {
      params: Promise.resolve({ topic, slug }),
    });
    expect(res.status).toBe(200);
    const attempt = JSON.parse(
      fs.readFileSync(
        path.join(fixtureDir, ".attempts", "node", "browser-kind.json"),
        "utf8",
      ),
    );
    expect(attempt.files).toEqual([{ lang: "js", code: "console.log('render me')" }]);
    expect(attempt.exitCode).toBeNull();
  });

  it("rejects without token", async () => {
    const req = new Request(
      "http://localhost:3000/api/challenges/node/browser-kind/attempt",
      {
        method: "POST",
        headers: { host: "localhost:3000" },
        body: JSON.stringify({ output: "x" }),
      },
    );
    const res = await attemptRoute.POST(req, {
      params: Promise.resolve({ topic: "node", slug: "browser-kind" }),
    });
    expect(res.status).toBe(403);
  });
});
