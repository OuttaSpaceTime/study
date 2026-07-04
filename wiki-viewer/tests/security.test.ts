// Tests for lib/security.ts — the CSRF/Host/Origin gate on mutating routes.
import { beforeAll, describe, expect, it } from "vitest";

type SecurityModule = typeof import("@/lib/security");

let mod: SecurityModule;

beforeAll(async () => {
  mod = await import("@/lib/security");
});

function request(headers: Record<string, string>): Request {
  return new Request("http://localhost:3000/api/challenges/a/b/run", {
    method: "POST",
    headers,
  });
}

describe("CSRF_TOKEN", () => {
  it("is a 32-char hex string", () => {
    expect(mod.CSRF_TOKEN).toMatch(/^[0-9a-f]{32}$/);
  });

  it("is stable across module re-imports (globalThis stash)", async () => {
    const again = await import("@/lib/security");
    expect(again.CSRF_TOKEN).toBe(mod.CSRF_TOKEN);
  });
});

describe("assertLocalMutation", () => {
  it("passes with valid host, same-origin Origin, and token", () => {
    const denied = mod.assertLocalMutation(
      request({
        host: "localhost:3000",
        origin: "http://localhost:3000",
        "x-study-csrf": mod.CSRF_TOKEN,
      }),
    );
    expect(denied).toBeNull();
  });

  it("passes with absent Origin plus valid token (curl / scripts)", () => {
    const denied = mod.assertLocalMutation(
      request({ host: "127.0.0.1:3000", "x-study-csrf": mod.CSRF_TOKEN }),
    );
    expect(denied).toBeNull();
  });

  it("rejects a foreign Host (DNS rebinding)", () => {
    const denied = mod.assertLocalMutation(
      request({ host: "evil.example:3000", "x-study-csrf": mod.CSRF_TOKEN }),
    );
    expect(denied?.status).toBe(403);
  });

  it("rejects Origin null (sandboxed iframe / opaque origin)", () => {
    const denied = mod.assertLocalMutation(
      request({
        host: "localhost:3000",
        origin: "null",
        "x-study-csrf": mod.CSRF_TOKEN,
      }),
    );
    expect(denied?.status).toBe(403);
  });

  it("rejects a cross-site Origin even with a valid token", () => {
    const denied = mod.assertLocalMutation(
      request({
        host: "localhost:3000",
        origin: "https://evil.example",
        "x-study-csrf": mod.CSRF_TOKEN,
      }),
    );
    expect(denied?.status).toBe(403);
  });

  it("rejects a missing token", () => {
    const denied = mod.assertLocalMutation(
      request({ host: "localhost:3000", origin: "http://localhost:3000" }),
    );
    expect(denied?.status).toBe(403);
  });

  it("rejects a wrong token", () => {
    const denied = mod.assertLocalMutation(
      request({
        host: "localhost:3000",
        origin: "http://localhost:3000",
        "x-study-csrf": "0".repeat(32),
      }),
    );
    expect(denied?.status).toBe(403);
  });
});
