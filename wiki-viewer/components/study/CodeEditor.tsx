"use client";

import CodeMirror, { type Extension } from "@uiw/react-codemirror";
import { html } from "@codemirror/lang-html";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { PostgreSQL, sql } from "@codemirror/lang-sql";
import { StreamLanguage } from "@codemirror/language";
import { ruby } from "@codemirror/legacy-modes/mode/ruby";

function languageFor(lang: string): Extension[] {
  switch (lang) {
    case "js":
    case "javascript":
    case "mjs":
      return [javascript()];
    case "jsx":
      return [javascript({ jsx: true })];
    case "ts":
    case "typescript":
      return [javascript({ typescript: true })];
    case "tsx":
      return [javascript({ typescript: true, jsx: true })];
    case "py":
    case "python":
      return [python()];
    case "sql":
    case "psql":
      return [sql({ dialect: PostgreSQL })];
    case "html":
      return [html()];
    case "css":
      return [html()];
    case "rb":
    case "ruby":
      return [StreamLanguage.define(ruby)];
    default:
      return [];
  }
}

export default function CodeEditor({
  value,
  lang,
  readOnly = false,
  onChange,
}: {
  value: string;
  lang: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}) {
  return (
    <div className="overflow-hidden rounded border border-border">
      <CodeMirror
        value={value}
        extensions={languageFor(lang)}
        readOnly={readOnly}
        editable={!readOnly}
        onChange={onChange}
        basicSetup={{ foldGutter: false, searchKeymap: false }}
        style={{ fontSize: "13px" }}
      />
    </div>
  );
}
