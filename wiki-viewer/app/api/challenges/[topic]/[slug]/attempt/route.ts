import type { AttemptRecord, AttemptStatus, CodeBlock } from "@/lib/challenge-types";
import { getChallenge, readAttempt, safeChallengeId, writeAttempt } from "@/lib/challenges";
import { assertLocalMutation } from "@/lib/security";

export const dynamic = "force-dynamic";

const STATUSES = new Set<AttemptStatus>(["ran", "pass", "differs", "error"]);

interface AttemptBody {
  files?: CodeBlock[];
  code?: string;
  output?: string;
  status?: string;
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

  const body = (await req.json().catch(() => ({}))) as AttemptBody;
  const previous = await readAttempt(id);
  const record: AttemptRecord = {
    id,
    kind: detail.meta.kind,
    env: detail.meta.env,
    ...(Array.isArray(body.files) ? { files: body.files } : {}),
    ...(typeof body.code === "string" ? { code: body.code } : {}),
    output: String(body.output ?? ""),
    exitCode: null,
    timedOut: false,
    status: STATUSES.has(body.status as AttemptStatus)
      ? (body.status as AttemptStatus)
      : "ran",
    runCount: (previous?.runCount ?? 0) + 1,
    updatedAt: new Date().toISOString(),
  };
  await writeAttempt(id, record);

  return Response.json({ ok: true, runCount: record.runCount });
}
