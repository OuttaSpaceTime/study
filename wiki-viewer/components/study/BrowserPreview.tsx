"use client";

import { useEffect, useRef } from "react";
import type { CodeBlock } from "@/lib/challenge-types";
import { buildSrcdoc } from "@/lib/srcdoc";

export default function BrowserPreview({
  files,
  preset,
  runKey,
  onConsole,
}: {
  files: CodeBlock[];
  preset: "react" | null;
  runKey: number;
  onConsole: (line: string) => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.source !== iframeRef.current?.contentWindow) return;
      const data = event.data as { type?: string; level?: string; text?: string };
      if (data?.type !== "study-console") return;
      onConsole(`[${data.level}] ${data.text}`);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [onConsole]);

  return (
    <iframe
      key={runKey}
      ref={iframeRef}
      sandbox="allow-scripts"
      srcDoc={buildSrcdoc(files, preset ?? undefined)}
      className="h-72 w-full rounded border border-border bg-white"
      title="Challenge preview"
    />
  );
}
