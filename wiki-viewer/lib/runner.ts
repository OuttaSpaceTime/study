// Server-side challenge execution. Everything that decides WHAT runs (env,
// command, cwd) comes from the challenge file + envs.json on disk — the
// request only ever supplies code strings. No shell is ever involved:
// execFile spawns the argv array directly.
import { execFile } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import type { ChallengeDetail, EnvEntry, RunResult } from "./challenge-types";

const pExecFile = promisify(execFile);

const DEFAULT_TIMEOUT_MS = 10_000;
const MAX_OUTPUT_BYTES = 64 * 1024;

const PG = {
  container: "study-pg",
  image: "postgres:17",
  host: "127.0.0.1",
  port: "55432",
  user: "postgres",
};

interface ExecOutcome {
  stdout: string;
  stderr: string;
  exitCode: number | null;
  timedOut: boolean;
}

async function exec(
  argv: string[],
  opts: { cwd?: string; timeoutMs: number },
): Promise<ExecOutcome> {
  try {
    const { stdout, stderr } = await pExecFile(argv[0]!, argv.slice(1), {
      cwd: opts.cwd,
      timeout: opts.timeoutMs,
      maxBuffer: MAX_OUTPUT_BYTES,
      killSignal: "SIGKILL",
      env: process.env,
    });
    return { stdout, stderr, exitCode: 0, timedOut: false };
  } catch (error) {
    const e = error as NodeJS.ErrnoException & {
      stdout?: string;
      stderr?: string;
      code?: number | string;
      killed?: boolean;
      signal?: string;
    };
    const timedOut =
      e.killed === true &&
      e.signal === "SIGKILL" &&
      e.code !== "ERR_CHILD_PROCESS_STDIO_MAXBUFFER";
    return {
      stdout: e.stdout ?? "",
      stderr: e.stderr ?? (typeof e.code === "string" ? `${e.code}: ${e.message}` : ""),
      exitCode: typeof e.code === "number" ? e.code : null,
      timedOut,
    };
  }
}

function labelOutput(outcome: ExecOutcome): string {
  let output = outcome.stdout;
  if (outcome.stderr.trim()) {
    output += (output ? "\n" : "") + "[stderr]\n" + outcome.stderr;
  }
  if (outcome.timedOut) {
    output += (output ? "\n" : "") + "[timed out]";
  }
  return output.slice(0, MAX_OUTPUT_BYTES);
}

async function runFileBased(
  env: EnvEntry,
  code: string,
  started: number,
): Promise<RunResult> {
  if (!env.command?.length) {
    throw new Error("env has no command");
  }
  const scratch = await fs.mkdtemp(path.join(os.tmpdir(), "study-run-"));
  try {
    const file = path.join(scratch, `main${env.ext ?? ""}`);
    await fs.writeFile(file, code);
    const argv = env.command.map((a) => a.replaceAll("{file}", file));
    const outcome = await exec(argv, {
      cwd: env.type === "project" ? env.cwd : scratch,
      timeoutMs: env.timeoutMs ?? DEFAULT_TIMEOUT_MS,
    });
    return {
      output: labelOutput(outcome),
      exitCode: outcome.timedOut ? null : outcome.exitCode,
      timedOut: outcome.timedOut,
      durationMs: Date.now() - started,
    };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
  }
}

async function ensureStudyPg(): Promise<void> {
  const state = await exec(
    ["docker", "inspect", "-f", "{{.State.Running}}", PG.container],
    { timeoutMs: 10_000 },
  );
  if (state.exitCode !== 0) {
    const run = await exec(
      [
        "docker", "run", "-d",
        "--name", PG.container,
        "-e", "POSTGRES_HOST_AUTH_METHOD=trust",
        "-p", `${PG.host}:${PG.port}:5432`,
        PG.image,
      ],
      { timeoutMs: 60_000 },
    );
    if (run.exitCode !== 0) throw new Error(`could not start ${PG.container}: ${run.stderr}`);
  } else if (state.stdout.trim() !== "true") {
    const start = await exec(["docker", "start", PG.container], { timeoutMs: 30_000 });
    if (start.exitCode !== 0) throw new Error(`could not start ${PG.container}: ${start.stderr}`);
  }
  for (let i = 0; i < 30; i++) {
    const ready = await exec(
      ["docker", "exec", PG.container, "pg_isready", "-U", PG.user],
      { timeoutMs: 5_000 },
    );
    if (ready.exitCode === 0) return;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`${PG.container} did not become ready`);
}

function psqlArgv(extra: string[]): string[] {
  return [
    "psql",
    "-h", PG.host,
    "-p", PG.port,
    "-U", PG.user,
    "-X",
    "-v", "ON_ERROR_STOP=1",
    ...extra,
  ];
}

async function runPostgres(
  detail: ChallengeDetail,
  env: EnvEntry,
  sql: string,
  started: number,
): Promise<RunResult> {
  await ensureStudyPg();
  const timeoutMs = env.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const dbName = `study_run_${crypto.randomBytes(4).toString("hex")}`;
  const scratch = await fs.mkdtemp(path.join(os.tmpdir(), "study-run-"));
  try {
    const create = await exec(
      psqlArgv(["-d", "postgres", "-c", `CREATE DATABASE ${dbName}`]),
      { timeoutMs },
    );
    if (create.exitCode !== 0) {
      throw new Error(`could not create scratch database: ${create.stderr}`);
    }
    const setupSql = detail.setup.map((b) => b.code).join("\n");
    if (setupSql.trim()) {
      const setupFile = path.join(scratch, "setup.sql");
      await fs.writeFile(setupFile, setupSql);
      const setup = await exec(psqlArgv(["-d", dbName, "-f", setupFile]), { timeoutMs });
      if (setup.exitCode !== 0) {
        return {
          output: "[setup failed]\n" + labelOutput(setup),
          exitCode: setup.exitCode,
          timedOut: setup.timedOut,
          durationMs: Date.now() - started,
        };
      }
    }
    const userFile = path.join(scratch, "main.sql");
    await fs.writeFile(userFile, sql);
    const outcome = await exec(psqlArgv(["-d", dbName, "-f", userFile]), { timeoutMs });
    return {
      output: labelOutput(outcome),
      exitCode: outcome.timedOut ? null : outcome.exitCode,
      timedOut: outcome.timedOut,
      durationMs: Date.now() - started,
    };
  } finally {
    await fs.rm(scratch, { recursive: true, force: true });
    await exec(
      psqlArgv(["-d", "postgres", "-c", `DROP DATABASE IF EXISTS ${dbName} WITH (FORCE)`]),
      { timeoutMs: 15_000 },
    );
  }
}

export async function runChallenge(
  detail: ChallengeDetail,
  env: EnvEntry,
  code: string,
): Promise<RunResult> {
  const started = Date.now();
  switch (env.type) {
    case "inline":
    case "project":
      return runFileBased(env, code, started);
    case "postgres":
      return runPostgres(detail, env, code, started);
    case "browser":
      throw new Error("browser challenges run client-side, not via the runner");
  }
}
