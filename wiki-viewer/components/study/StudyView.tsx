"use client";

import { useCallback, useRef, useState } from "react";
import type {
  AttemptRecord,
  AttemptStatus,
  CodeBlock,
  StudyPayload,
} from "@/lib/challenge-types";
import BrowserPreview from "./BrowserPreview";
import CodeEditor from "./CodeEditor";
import OutputPanel from "./OutputPanel";
import PredictDiff from "./PredictDiff";

interface RunState {
  output: string;
  status: AttemptStatus;
  exitCode: number | null;
  timedOut: boolean;
  durationMs: number | null;
  runCount: number;
}

export default function StudyView({
  payload,
  initialAttempt,
  csrfToken,
}: {
  payload: StudyPayload;
  initialAttempt: AttemptRecord | null;
  csrfToken: string;
}) {
  const { meta } = payload;
  const isBrowser = meta.envType === "browser";
  const isPredict = meta.kind === "predict-output";

  const [files, setFiles] = useState<CodeBlock[]>(() => {
    if (initialAttempt?.files?.length) return initialAttempt.files;
    if (initialAttempt?.code && payload.stub.length === 1) {
      return [{ lang: payload.stub[0]!.lang, code: initialAttempt.code }];
    }
    return payload.stub;
  });
  const [prediction, setPrediction] = useState(initialAttempt?.predictedOutput ?? "");
  const [result, setResult] = useState<RunState | null>(null);
  const [running, setRunning] = useState(false);
  const [staleServer, setStaleServer] = useState(false);
  const [runKey, setRunKey] = useState(0);
  const [previewLive, setPreviewLive] = useState(false);
  const consoleLines = useRef<string[]>([]);
  const runCount = useRef(initialAttempt?.runCount ?? 0);

  const onConsole = useCallback((line: string) => {
    consoleLines.current.push(line);
    setResult((prev) =>
      prev
        ? { ...prev, output: consoleLines.current.join("\n") }
        : {
            output: consoleLines.current.join("\n"),
            status: "ran",
            exitCode: null,
            timedOut: false,
            durationMs: null,
            runCount: runCount.current,
          },
    );
  }, []);

  async function persistBrowserAttempt() {
    const res = await fetch(`/api/challenges/${meta.id}/attempt`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-study-csrf": csrfToken },
      body: JSON.stringify({
        files,
        output: consoleLines.current.join("\n"),
        status: "ran",
      }),
    });
    if (res.status === 403) setStaleServer(true);
    if (res.ok) {
      const data = (await res.json()) as { runCount: number };
      runCount.current = data.runCount;
      setResult((prev) => (prev ? { ...prev, runCount: data.runCount } : prev));
    }
  }

  async function run() {
    setRunning(true);
    setStaleServer(false);
    try {
      if (isBrowser) {
        consoleLines.current = [];
        setResult({
          output: "",
          status: "ran",
          exitCode: null,
          timedOut: false,
          durationMs: null,
          runCount: runCount.current + 1,
        });
        setRunKey((k) => k + 1);
        setPreviewLive(true);
        await persistBrowserAttempt();
        return;
      }
      const body = isPredict
        ? { predictedOutput: prediction }
        : { code: files.map((f) => f.code).join("\n") };
      const res = await fetch(`/api/challenges/${meta.id}/run`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-study-csrf": csrfToken },
        body: JSON.stringify(body),
      });
      if (res.status === 403) {
        setStaleServer(true);
        return;
      }
      if (!res.ok) {
        const detail = (await res.json().catch(() => null)) as { error?: string } | null;
        setResult({
          output: detail?.error ?? `request failed (${res.status})`,
          status: "error",
          exitCode: null,
          timedOut: false,
          durationMs: null,
          runCount: runCount.current,
        });
        return;
      }
      const data = (await res.json()) as RunState;
      runCount.current = data.runCount;
      setResult(data);
    } finally {
      setRunning(false);
    }
  }

  const runDisabled = running || (isPredict && !prediction.trim());

  return (
    <div className="space-y-5">
      {staleServer && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-[13px] text-amber-900">
          The server restarted — reload the page to keep working.
        </div>
      )}

      <div className="space-y-3">
        {files.map((file, i) => (
          <div key={`${file.lang}-${i}`}>
            {files.length > 1 && (
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-faint">
                {file.lang}
              </div>
            )}
            <CodeEditor
              value={file.code}
              lang={file.lang}
              readOnly={isPredict}
              onChange={(code) =>
                setFiles((prev) => prev.map((f, j) => (j === i ? { ...f, code } : f)))
              }
            />
          </div>
        ))}
      </div>

      {isPredict && (
        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-faint">
            Your predicted output — write it before running
          </div>
          <textarea
            value={prediction}
            onChange={(e) => setPrediction(e.target.value)}
            rows={5}
            spellCheck={false}
            className="w-full rounded border border-border bg-panel px-3 py-2 font-mono text-[13px] text-fg outline-none focus:border-accent"
            placeholder="What will this print?"
          />
        </div>
      )}

      {payload.expectedOutput !== null && !isPredict && (
        <div>
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-faint">
            Target output
          </div>
          <pre className="overflow-x-auto rounded border border-border bg-panel-2 px-3 py-2 font-mono text-[13px] text-fg">
            {payload.expectedOutput}
          </pre>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={run}
          disabled={runDisabled}
          className="rounded bg-accent px-4 py-1.5 text-[14px] font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {running ? "Running…" : "Run"}
        </button>
        {isPredict && !prediction.trim() && (
          <span className="text-[13px] text-faint">predict the output first</span>
        )}
      </div>

      {isBrowser && previewLive && (
        <BrowserPreview
          files={files}
          preset={meta.envPreset}
          runKey={runKey}
          onConsole={onConsole}
        />
      )}

      {result && isPredict && !result.timedOut && result.exitCode === 0 && (
        <PredictDiff predicted={prediction} actual={result.output} />
      )}

      {result && (
        <OutputPanel
          output={result.output}
          status={result.status}
          exitCode={result.exitCode}
          timedOut={result.timedOut}
          durationMs={result.durationMs}
          runCount={result.runCount}
        />
      )}
    </div>
  );
}
