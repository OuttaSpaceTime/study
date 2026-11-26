import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import { createDeckClient, deckCall, type DeckClient } from "@/lib/deck-client";

const FAKE = path.join(import.meta.dirname, "fixtures", "fake-deck-server.mjs");

const clients: DeckClient[] = [];
function make(
  options: {
    timeoutMs?: number;
    startupTimeoutMs?: number;
    failFastMs?: number;
    env?: Record<string, string>;
  } = {},
) {
  const client = createDeckClient({ command: process.execPath, args: [FAKE], ...options });
  clients.push(client);
  return client;
}

afterEach(() => {
  while (clients.length) clients.pop()?.close();
});

describe("deck client", () => {
  it("returns the result of a call", async () => {
    const client = make();
    expect(await client.call("echo", { a: 1 })).toEqual({ a: 1 });
  });

  it("matches concurrent responses to their requests by id", async () => {
    const client = make();
    const [slow, fast] = await Promise.all([
      client.call("delay", { ms: 150, value: "slow" }),
      client.call("delay", { ms: 5, value: "fast" }),
    ]);
    expect([slow, fast]).toEqual(["slow", "fast"]);
  });

  it("rejects with the server's message on an error reply", async () => {
    const client = make();
    await expect(client.call("fail")).rejects.toThrow("boom");
    // The connection is still usable afterwards.
    expect(await client.call("echo", { ok: true })).toEqual({ ok: true });
  });

  it("starts one child for many calls", async () => {
    const client = make({ env: { FAKE_DECK_STARTUP_MS: "50" } });
    const pids = await Promise.all([client.call("pid"), client.call("pid"), client.call("pid")]);
    expect(new Set(pids).size).toBe(1);
  });

  it("times out a call the server never answers", async () => {
    const client = make({ timeoutMs: 100 });
    await expect(client.call("hang")).rejects.toThrow(/timed out/);
  });

  it("rejects pending calls when the child exits, then restarts on the next call", async () => {
    const client = make();
    const firstPid = await client.call<number>("pid");
    await expect(client.call("exit")).rejects.toThrow(/exited/);
    const secondPid = await client.call<number>("pid");
    expect(secondPid).not.toBe(firstPid);
  });

  it("rejects when the command cannot be started", async () => {
    const client = createDeckClient({ command: "/nonexistent/deck-server" });
    clients.push(client);
    await expect(client.call("echo")).rejects.toThrow();
  });

  it("rejects when the child never says ready", async () => {
    const client = make({ startupTimeoutMs: 100, env: { FAKE_DECK_STARTUP_MS: "5000" } });
    await expect(client.call("echo")).rejects.toThrow(/ready/);
  });

  it("reassembles a reply line split across two chunks", async () => {
    const client = make();
    expect(await client.call("split")).toBe("joined");
  });

  it("handles a reply line larger than a pipe buffer", async () => {
    const client = make();
    const result = await client.call<string>("big", { bytes: 300_000 });
    expect(result).toHaveLength(300_000);
  });

  it("kills a child that timed out and starts a new one on the next call", async () => {
    const client = make({ timeoutMs: 150 });
    const wedged = await client.call<number>("pid");
    await expect(client.call("hang")).rejects.toThrow(/timed out/);
    const fresh = await client.call<number>("pid");
    expect(fresh).not.toBe(wedged);
    await new Promise((r) => setTimeout(r, 100));
    expect(() => process.kill(wedged, 0)).toThrow();
  });

  it("fails fast after a boot failure, then starts again once the window passes", async () => {
    const marker = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "deck-client-")), "crashed");
    const client = make({ failFastMs: 400, env: { FAKE_DECK_CRASH_ONCE: marker } });
    await expect(client.call("echo")).rejects.toThrow(/exited/);
    // A real spawn would boot fine now (the marker exists), so a rejection here
    // can only be the remembered error.
    const started = Date.now();
    await expect(client.call("echo")).rejects.toThrow(/exited/);
    expect(Date.now() - started).toBeLessThan(100);
    await new Promise((r) => setTimeout(r, 450));
    expect(await client.call("echo", { ok: 1 })).toEqual({ ok: 1 });
  });
});

describe("deckCall with a missing deck database", () => {
  it("fails loudly and creates nothing, before any server is started", async () => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "deck-missing-"));
    const missing = path.join(dir, "typo.db");
    const saved = { dir: process.env.FLASHCARD_MCP_DIR, db: process.env.FLASHCARD_DB };
    process.env.FLASHCARD_MCP_DIR = dir;
    process.env.FLASHCARD_DB = missing;
    try {
      await expect(deckCall("cardRecords")).rejects.toThrow(/No deck database at .*typo\.db.*\.env\.local/);
      expect(fs.existsSync(missing)).toBe(false);
    } finally {
      for (const [key, value] of [["FLASHCARD_MCP_DIR", saved.dir], ["FLASHCARD_DB", saved.db]] as const) {
        if (value === undefined) delete process.env[key];
        else process.env[key] = value;
      }
    }
  });
});
