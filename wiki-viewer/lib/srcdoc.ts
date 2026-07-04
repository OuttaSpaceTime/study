// Builds the srcdoc for the sandboxed challenge iframe (sandbox="allow-scripts",
// no allow-same-origin → opaque origin, so nothing in here can reach /api/*).
// Pure string composition — used by the server ChallengeBlock and the client
// BrowserPreview alike.
import type { CodeBlock } from "./challenge-types";

const CONSOLE_CAPTURE = `
(function () {
  function send(level, args) {
    var text = Array.prototype.map.call(args, function (a) {
      if (typeof a === "object") { try { return JSON.stringify(a); } catch (e) { return String(a); } }
      return String(a);
    }).join(" ");
    parent.postMessage({ type: "study-console", level: level, text: text }, "*");
  }
  ["log", "info", "warn", "error"].forEach(function (level) {
    var original = console[level];
    console[level] = function () { send(level, arguments); original.apply(console, arguments); };
  });
  window.onerror = function (message, source, line) {
    send("error", [message + " (line " + line + ")"]);
  };
})();
`;

function escapeScript(code: string): string {
  return code.replaceAll("</script", "<\\/script");
}

function collect(files: CodeBlock[], ...langs: string[]): string {
  return files
    .filter((f) => langs.includes(f.lang))
    .map((f) => f.code)
    .join("\n");
}

export function buildSrcdoc(files: CodeBlock[], preset?: "react"): string {
  const css = collect(files, "css");
  const html = collect(files, "html");

  if (preset === "react") {
    const jsx = collect(files, "jsx", "js", "tsx");
    return [
      "<!doctype html><html><head><meta charset=\"utf-8\">",
      `<style>${css}</style>`,
      "</head><body>",
      html || '<div id="root"></div>',
      `<script>${escapeScript(CONSOLE_CAPTURE)}</script>`,
      '<script src="/vendor/react.production.min.js"></script>',
      '<script src="/vendor/react-dom.production.min.js"></script>',
      '<script src="/vendor/babel.min.js"></script>',
      `<script type="text/babel" data-presets="react">${escapeScript(jsx)}</script>`,
      "</body></html>",
    ].join("\n");
  }

  const js = collect(files, "js", "javascript");
  return [
    "<!doctype html><html><head><meta charset=\"utf-8\">",
    `<style>${css}</style>`,
    "</head><body>",
    html,
    `<script>${escapeScript(CONSOLE_CAPTURE)}</script>`,
    `<script>${escapeScript(js)}</script>`,
    "</body></html>",
  ].join("\n");
}
