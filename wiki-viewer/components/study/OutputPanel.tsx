"use client";

import clsx from "clsx";
import type { AttemptStatus } from "@/lib/challenge-types";

const STATUS_STYLES: Record<AttemptStatus, string> = {
  pass: "bg-green-100 text-green-800",
  differs: "bg-amber-100 text-amber-800",
  error: "bg-red-100 text-red-800",
  ran: "bg-panel-2 text-muted",
};

export default function OutputPanel({
  output,
  status,
  exitCode,
  timedOut,
  durationMs,
  runCount,
}: {
  output: string;
  status: AttemptStatus;
  exitCode: number | null;
  timedOut: boolean;
  durationMs: number | null;
  runCount: number;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-faint">
          Output
        </span>
        <span
          className={clsx(
            "rounded px-1.5 py-0.5 text-[11px] font-medium",
            STATUS_STYLES[status],
          )}
        >
          {timedOut ? "timed out" : status}
        </span>
        {exitCode !== null && exitCode !== 0 && (
          <span className="text-[11px] text-faint">exit {exitCode}</span>
        )}
        {durationMs !== null && (
          <span className="text-[11px] text-faint">{durationMs} ms</span>
        )}
        <span className="ml-auto text-[11px] text-faint">
          run {runCount}
        </span>
      </div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded border border-border bg-panel-2 px-3 py-2 font-mono text-[13px] text-fg">
        {output || "(no output)"}
      </pre>
    </div>
  );
}
