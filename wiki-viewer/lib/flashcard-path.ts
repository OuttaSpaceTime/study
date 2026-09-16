// Server-only. Machine-local paths live in .env.local at the repo root, which
// is gitignored so the two laptops that share this repo never overwrite each
// other's checkout locations. Env vars still win, for one-off overrides.
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Walk up from cwd to the repo root, identified by AGENTS.md sitting next to wiki/. */
function findRepoRoot(): string {
  let dir = process.cwd();
  for (;;) {
    if (existsSync(path.join(dir, "AGENTS.md")) && existsSync(path.join(dir, "wiki"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return process.cwd();
    dir = parent;
  }
}

export const REPO_ROOT = findRepoRoot();

function readEnvLocal(): Record<string, string> {
  const file = path.join(REPO_ROOT, ".env.local");
  if (!existsSync(file)) return {};
  const values: Record<string, string> = {};
  for (const raw of readFileSync(file, "utf8").split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    values[line.slice(0, eq).trim()] = line.slice(eq + 1).trim().replace(/^["']|["']$/g, "");
  }
  return values;
}

function expandHome(value: string): string {
  if (value.startsWith("~/")) return path.join(process.env.HOME ?? "", value.slice(2));
  if (value.startsWith("$HOME/")) return path.join(process.env.HOME ?? "", value.slice(6));
  return value;
}

/** Null rather than throwing: both callers degrade to an empty panel instead of a 500. */
export function flashcardMcpDir(): string | null {
  const value = process.env.FLASHCARD_MCP_DIR ?? readEnvLocal().FLASHCARD_MCP_DIR;
  return value ? expandHome(value) : null;
}

export function masterDbPath(): string | null {
  if (process.env.FLASHCARD_DB) return process.env.FLASHCARD_DB;
  const dir = flashcardMcpDir();
  return dir ? path.join(dir, "prisma", "master.db") : null;
}
