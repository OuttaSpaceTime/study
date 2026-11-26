// Server-only: never import this (or lib/flashcards, lib/calibration) from a
// client component; it spawns a child process. tests/server-only.test.ts checks it.
// The viewer's one connection to the deck. flashcard-mcp owns
// master.db and its schema; this file speaks to its app server (NDJSON over
// stdio, src/app/server.ts) instead of opening the SQLite file, so the viewer
// holds no second reader of the schema and no copy of the calibration rule.
//
// One long-lived child per Next server process: a start costs about a second of
// tsx, far too much per request. Started on the first call, restarted on the
// next call after it dies.
import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import { createInterface } from "node:readline";
import { flashcardMcpDir, masterDbPath } from "./flashcard-path";

export interface DeckClientOptions {
  command: string;
  args?: readonly string[];
  cwd?: string;
  env?: Record<string, string>;
  /** Per call, once the child is up. */
  timeoutMs?: number;
  /** Waiting for `{"ready": true}`: tsx plus opening the database. */
  startupTimeoutMs?: number;
  /** After a failed start, calls fail at once with that error for this long. */
  failFastMs?: number;
}

export interface DeckClient {
  call<T>(method: string, params?: Record<string, unknown>): Promise<T>;
  close(): void;
}

interface Pending {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
  timer: NodeJS.Timeout;
}

/** A client over any command that speaks the app-server protocol. Exported for tests. */
export function createDeckClient(options: DeckClientOptions): DeckClient {
  const timeoutMs = options.timeoutMs ?? 10_000;
  const failFastMs = options.failFastMs ?? 5_000;
  const startupTimeoutMs = options.startupTimeoutMs ?? 10_000;

  let child: ChildProcess | null = null;
  let starting: Promise<ChildProcess> | null = null;
  // A boot failure (bad path, broken install, locked db) repeats on every
  // spawn; without this each page request would pay for a doomed tsx start.
  let lastStartFailure: { error: Error; at: number } | null = null;
  let nextId = 1;
  const pending = new Map<number, Pending>();

  function failAll(error: Error): void {
    for (const entry of pending.values()) {
      clearTimeout(entry.timer);
      entry.reject(error);
    }
    pending.clear();
  }

  function onLine(line: string): void {
    let message: { id?: unknown; result?: unknown; error?: { message?: string } };
    try {
      message = JSON.parse(line) as typeof message;
    } catch {
      return;
    }
    if (typeof message.id !== "number") return;
    const entry = pending.get(message.id);
    if (!entry) return;
    pending.delete(message.id);
    clearTimeout(entry.timer);
    if (message.error) entry.reject(new Error(message.error.message ?? "deck server error"));
    else entry.resolve(message.result);
  }

  function start(): Promise<ChildProcess> {
    return new Promise((resolve, reject) => {
      const proc = spawn(options.command, [...(options.args ?? [])], {
        cwd: options.cwd,
        env: { ...process.env, ...options.env },
        stdio: ["pipe", "pipe", "pipe"],
      });
      let ready = false;
      const startupTimer = setTimeout(() => {
        proc.kill();
        reject(new Error("deck server did not become ready in time"));
      }, startupTimeoutMs);

      const lines = createInterface({ input: proc.stdout! });
      lines.on("line", (line) => {
        if (!ready) {
          if (line.includes('"ready"')) {
            ready = true;
            clearTimeout(startupTimer);
            resolve(proc);
          }
          return;
        }
        onLine(line);
      });
      // Drained, or a chatty child would block on a full pipe.
      proc.stderr!.resume();
      // A write to a dead child: fail everything waiting at once and drop it,
      // so the next call restarts instead of waiting out each timeout.
      proc.stdin!.on("error", (err) => {
        failAll(err);
        proc.kill();
      });

      proc.on("error", (err) => {
        clearTimeout(startupTimer);
        if (child === proc) child = null;
        failAll(err);
        reject(err);
      });
      proc.on("exit", (code) => {
        clearTimeout(startupTimer);
        if (child === proc) child = null;
        const error = new Error(`deck server exited (code ${code ?? "signal"})`);
        failAll(error);
        reject(error); // a no-op once ready
      });
    });
  }

  async function ensureChild(): Promise<ChildProcess> {
    if (child && child.exitCode === null && !child.killed) return child;
    if (lastStartFailure && Date.now() - lastStartFailure.at < failFastMs) {
      throw lastStartFailure.error;
    }
    starting ??= start()
      .then((proc) => {
        child = proc;
        lastStartFailure = null;
        return proc;
      })
      .catch((err: unknown) => {
        const error = err instanceof Error ? err : new Error(String(err));
        lastStartFailure = { error, at: Date.now() };
        throw error;
      })
      .finally(() => {
        starting = null;
      });
    return starting;
  }

  return {
    async call<T>(method: string, params: Record<string, unknown> = {}): Promise<T> {
      const proc = await ensureChild();
      return new Promise<T>((resolve, reject) => {
        const id = nextId++;
        const timer = setTimeout(() => {
          pending.delete(id);
          reject(new Error(`deck call "${method}" timed out`));
          // A server that stopped answering is wedged; kill it so the next
          // call starts a fresh one. Its exit rejects the other waiting calls.
          proc.kill();
        }, timeoutMs);
        pending.set(id, { resolve: resolve as (v: unknown) => void, reject, timer });
        proc.stdin!.write(JSON.stringify({ id, method, params }) + "\n");
      });
    },
    close(): void {
      failAll(new Error("deck client closed"));
      child?.kill();
      child = null;
    },
  };
}

// Next's dev server reloads modules on every edit; keeping the client on
// globalThis stops each reload from leaving another child behind.
const globalStore = globalThis as { __deckClient?: DeckClient };

function appClient(): DeckClient {
  if (globalStore.__deckClient) return globalStore.__deckClient;
  const dir = flashcardMcpDir();
  const db = masterDbPath();
  if (!dir || !db) {
    throw new Error("FLASHCARD_MCP_DIR is not set — add it to .env.local at the repo root.");
  }
  globalStore.__deckClient = createDeckClient({
    command: path.join(dir, "node_modules", ".bin", "tsx"),
    args: ["src/app/server.ts"],
    cwd: dir,
    env: { DATABASE_URL: `file:${db}`, NODE_NO_WARNINGS: "1" },
  });
  return globalStore.__deckClient;
}

/** Call a deck app-server method; rejects with the server's message on an error. */
export async function deckCall<T>(
  method: string,
  params: Record<string, unknown> = {},
): Promise<T> {
  return appClient().call<T>(method, params);
}
