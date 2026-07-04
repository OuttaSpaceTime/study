import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Markdown from "react-markdown";
import StudyView from "@/components/study/StudyView";
import { getChallenge, readAttempt, safeChallengeId, toStudyPayload } from "@/lib/challenges";
import { slugifyHeading } from "@/lib/markdown";
import { CSRF_TOKEN } from "@/lib/security";

export const dynamic = "force-dynamic";

interface RouteParams {
  topic: string;
  slug: string;
}

function idFrom(params: RouteParams): string {
  return `${decodeURIComponent(params.topic)}/${decodeURIComponent(params.slug)}`;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const id = idFrom(await params);
  return { title: `${id} · Challenge · Study Wiki` };
}

export default async function StudyPage({
  params,
}: {
  params: Promise<RouteParams>;
}) {
  const id = idFrom(await params);
  if (!safeChallengeId(id)) notFound();
  const detail = await getChallenge(id);
  if (!detail) notFound();

  const payload = toStudyPayload(detail);
  const attempt = await readAttempt(id);
  const { meta } = payload;

  return (
    <div className="mx-auto w-full max-w-3xl px-8 py-12">
      <header className="mb-8">
        <div className="mb-2 flex items-center gap-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-faint">
            Challenge
          </span>
          <span className="rounded bg-panel-2 px-1.5 py-0.5 text-[11px] text-muted">
            {meta.kind}
          </span>
          <span className="rounded bg-panel-2 px-1.5 py-0.5 text-[11px] text-muted">
            {meta.env}
          </span>
        </div>
        <h1 className="text-2xl font-semibold text-fg">{meta.slug}</h1>
        {meta.wiki && meta.section && (
          <Link
            href={`/wiki/${meta.wiki}#${slugifyHeading(meta.section)}`}
            className="mt-1 inline-block text-[13px] text-accent hover:underline"
          >
            ← {meta.wiki} · {meta.section}
          </Link>
        )}
      </header>

      {payload.brief && (
        <div className="wiki-prose prose mb-6 max-w-none">
          <Markdown>{payload.brief}</Markdown>
        </div>
      )}

      <StudyView payload={payload} initialAttempt={attempt} csrfToken={CSRF_TOKEN} />

      {meta.questions.length > 0 && (
        <section className="mt-8 rounded-lg border border-border bg-panel px-4 py-4">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-faint">
            Questions — answer in chat with “challenge finished: …”
          </div>
          <ol className="list-decimal space-y-1 pl-5 text-[14px] text-muted">
            {meta.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
