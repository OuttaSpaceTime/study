import type { AttemptRecord, ChallengeDetail, RunResult } from "@/lib/challenge-types";
import {
  getChallenge,
  getEnvRegistry,
  readAttempt,
  safeChallengeId,
  writeAttempt,
} from "@/lib/challenges";
import { runChallenge } from "@/lib/runner";
import { assertLocalMutation } from "@/lib/security";

export const dynamic = "force-dynamic";

interface RunBody {
  code?: string;
  predictedOutput?: string;
}

function normalizeOutput(text: string): string {
  return text
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();
}

function computeStatus(
  detail: ChallengeDetail,
  body: RunBody,
  result: RunResult,
): AttemptRecord["status"] {
  if (result.timedOut || result.exitCode !== 0) return "error";
  if (detail.meta.kind === "predict-output") {
    return normalizeOutput(body.predictedOutput ?? "") === normalizeOutput(result.output)
      ? "pass"
      : "differs";
  }
  if (detail.expectedOutput !== null) {
    return normalizeOutput(result.output) === normalizeOutput(detail.expectedOutput)
      ? "pass"
      : "differs";
  }
  return "ran";
}

export async function POST(
  req: Request,
  ctx: { params: Promise<{ topic: string; slug: string }> },
) {
  const denied = assertLocalMutation(req);
  if (denied) return denied;

  const { topic, slug } = await ctx.params;
  const id = `${decodeURIComponent(topic)}/${decodeURIComponent(slug)}`;
  if (!safeChallengeId(id)) return new Response("Not found", { status: 404 });

  const detail = await getChallenge(id);
  if (!detail) return new Response("Not found", { status: 404 });

  const envs = await getEnvRegistry();
  const env = envs[detail.meta.env];
  if (!env) {
    return Response.json(
      { error: `env '${detail.meta.env}' is not in challenges/envs.json` },
      { status: 500 },
    );
  }
  if (env.type === "browser") {
    return Response.json(
      { error: "browser challenges render client-side; persist via /attempt" },
      { status: 400 },
    );
  }

  const body = (await req.json().catch(() => ({}))) as RunBody;
  const code =
    detail.meta.kind === "predict-output"
      ? detail.stub.map((b) => b.code).join("\n")
      : String(body.code ?? "");

  let result: RunResult;
  try {
    result = await runChallenge(detail, env, code);
  } catch (error) {
    return Response.json({ error: String(error) }, { status: 500 });
  }

  const status = computeStatus(detail, body, result);
  const previous = await readAttempt(id);
  const record: AttemptRecord = {
    id,
    kind: detail.meta.kind,
    env: detail.meta.env,
    ...(detail.meta.kind === "write-code" ? { code: String(body.code ?? "") } : {}),
    ...(detail.meta.kind === "predict-output"
      ? { predictedOutput: String(body.predictedOutput ?? "") }
      : {}),
    output: result.output,
    exitCode: result.exitCode,
    timedOut: result.timedOut,
    status,
    runCount: (previous?.runCount ?? 0) + 1,
    updatedAt: new Date().toISOString(),
  };
  await writeAttempt(id, record);

  return Response.json({ ...result, status, runCount: record.runCount });
}
