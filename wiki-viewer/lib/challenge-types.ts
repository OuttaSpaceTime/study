// Shared contract between the challenge data layer, the API routes, and the
// study/view UI. Pure types + one normalization helper — importable anywhere.

export type ChallengeKind = "write-code" | "predict-output";

export type EnvType = "inline" | "project" | "postgres" | "browser";

export interface CodeBlock {
  lang: string;
  code: string;
}

export interface ChallengeMeta {
  /** Challenges-relative path without extension, always "<topic>/<slug>". */
  id: string;
  topic: string;
  slug: string;
  /** Linked wiki page path, or null for scratch challenges. */
  wiki: string | null;
  /** Linked H2 heading text as written, or null for scratch challenges. */
  section: string | null;
  sectionNorm: string | null;
  kind: ChallengeKind;
  env: string;
  /** Denormalized from envs.json so the client knows run vs iframe; null if the env id is unknown. */
  envType: EnvType | null;
  /** Denormalized browser-env preset (react loads the vendored UMD runtime). */
  envPreset: "react" | null;
  questions: string[];
  created: string;
}

export interface ChallengeDetail {
  meta: ChallengeMeta;
  /** Markdown prose from ## Brief. */
  brief: string;
  /** Fenced blocks from ## Setup (postgres seed SQL). */
  setup: CodeBlock[];
  /** Fenced blocks from ## Stub. */
  stub: CodeBlock[];
  /** Fenced blocks from ## Solution. Never sent to the study client. */
  solution: CodeBlock[];
  /** Content of the ## Expected Output fence, or null. */
  expectedOutput: string | null;
}

/** Client-safe study payload — built ONLY via toStudyPayload, never carries the solution. */
export interface StudyPayload {
  meta: ChallengeMeta;
  brief: string;
  stub: CodeBlock[];
  /** Target output for write-code; null for predict-output (that is the exercise). */
  expectedOutput: string | null;
}

export interface EnvEntry {
  type: EnvType;
  /** Argv template; "{file}" is replaced element-wise with the temp file path. */
  command?: string[];
  ext?: string;
  cwd?: string;
  timeoutMs?: number;
  preset?: "react";
}

export interface RunResult {
  output: string;
  exitCode: number | null;
  timedOut: boolean;
  durationMs: number;
}

export type AttemptStatus = "ran" | "pass" | "differs" | "error";

export interface AttemptRecord {
  id: string;
  kind: ChallengeKind;
  env: string;
  code?: string;
  files?: CodeBlock[];
  predictedOutput?: string;
  output: string;
  exitCode: number | null;
  timedOut: boolean;
  status: AttemptStatus;
  runCount: number;
  updatedAt: string;
}

/** Mirrors normalize_heading in the study repo's scripts/wiki/frontmatter.py:
 *  strip, drop trailing .?!: runs, lowercase. The two sides must agree or
 *  lint-valid challenges would not surface in the viewer. */
export function normalizeSection(text: string): string {
  return text.trim().replace(/[.?!:]+$/, "").toLowerCase();
}
