// Server component: the fulfilled challenge shown under its H2 in view mode —
// solution, output (live iframe for browser envs), and the review questions.
import Link from "next/link";
import Markdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import type { ChallengeDetail, CodeBlock } from "@/lib/challenge-types";
import { buildSrcdoc } from "@/lib/srcdoc";

function refence(blocks: CodeBlock[]): string {
  return blocks.map((b) => `\`\`\`${b.lang}\n${b.code}\n\`\`\``).join("\n\n");
}

export default function ChallengeBlock({ challenge }: { challenge: ChallengeDetail }) {
  const { meta } = challenge;
  return (
    <details className="not-prose group my-5 rounded-lg border border-border bg-panel shadow-sm">
      <summary className="flex cursor-pointer select-none items-center gap-2.5 px-4 py-2.5 [&::-webkit-details-marker]:hidden">
        <span className="text-faint transition-transform group-open:rotate-90">▸</span>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-faint">
          Challenge
        </span>
        <span className="rounded bg-panel-2 px-1.5 py-0.5 text-[11px] text-muted">
          {meta.kind}
        </span>
        <span className="rounded bg-panel-2 px-1.5 py-0.5 text-[11px] text-muted">
          {meta.env}
        </span>
        <Link
          href={`/study/${meta.id}`}
          className="ml-auto text-[13px] font-medium text-accent hover:underline"
        >
          Practice →
        </Link>
      </summary>
      <div className="space-y-4 border-t border-border px-4 py-4">
        {challenge.brief && (
          <div className="wiki-prose prose prose-sm max-w-none">
            <Markdown>{challenge.brief}</Markdown>
          </div>
        )}
        <div className="wiki-prose prose prose-sm max-w-none">
          <Markdown rehypePlugins={[rehypeHighlight]}>
            {refence(challenge.solution)}
          </Markdown>
        </div>
        {meta.envType === "browser" ? (
          <iframe
            sandbox="allow-scripts"
            srcDoc={buildSrcdoc(challenge.solution, meta.envPreset ?? undefined)}
            className="h-56 w-full rounded border border-border bg-white"
            title={`Rendered output of ${meta.id}`}
          />
        ) : challenge.expectedOutput ? (
          <div>
            <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-faint">
              Output
            </div>
            <pre className="overflow-x-auto rounded border border-border bg-panel-2 px-3 py-2 font-mono text-[13px] text-fg">
              {challenge.expectedOutput}
            </pre>
          </div>
        ) : null}
        {meta.questions.length > 0 && (
          <div>
            <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-faint">
              Review questions
            </div>
            <ul className="list-disc space-y-1 pl-5 text-[14px] text-muted">
              {meta.questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}
