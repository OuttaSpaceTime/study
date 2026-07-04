"use client";

import { diffLines } from "diff";
import clsx from "clsx";

function normalize(text: string): string {
  const body = text
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();
  return body ? body + "\n" : "";
}

export default function PredictDiff({
  predicted,
  actual,
}: {
  predicted: string;
  actual: string;
}) {
  const parts = diffLines(normalize(predicted), normalize(actual));
  const match = parts.every((p) => !p.added && !p.removed);
  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-faint">
          Prediction vs actual
        </span>
        <span
          className={clsx(
            "rounded px-1.5 py-0.5 text-[11px] font-medium",
            match ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800",
          )}
        >
          {match ? "match" : "differs"}
        </span>
      </div>
      <pre className="max-h-72 overflow-auto rounded border border-border bg-panel-2 px-3 py-2 font-mono text-[13px]">
        {parts.map((part, i) => (
          <span
            key={i}
            className={clsx(
              part.added && "block bg-green-50 text-green-900",
              part.removed && "block bg-red-50 text-red-900 line-through decoration-red-300",
              !part.added && !part.removed && "block text-muted",
            )}
          >
            {part.value
              .replace(/\n$/, "")
              .split("\n")
              .map((line) => `${part.added ? "+ " : part.removed ? "− " : "  "}${line}`)
              .join("\n")}
          </span>
        ))}
      </pre>
    </div>
  );
}
