// The deck client spawns a child process, so the modules that reach it must
// never end up in a client bundle. Next only fails that at build time; this
// fails it in the test run.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = path.resolve(import.meta.dirname, "..");
const SERVER_ONLY = ["lib/deck-client", "lib/flashcards", "lib/calibration"].map((p) =>
  path.join(ROOT, p),
);

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.(ts|tsx)$/.test(entry.name) ? [full] : [];
  });
}

function importsOf(file: string, text: string): string[] {
  const specs = [...text.matchAll(/(?:from|import)\s*\(?\s*["']([^"']+)["']/g)].map((m) => m[1]!);
  return specs.map((spec) =>
    spec.startsWith("@/") ? path.join(ROOT, spec.slice(2)) : path.resolve(path.dirname(file), spec),
  );
}

describe("server-only deck modules", () => {
  const files = ["components", "app", "lib"].flatMap((d) => sourceFiles(path.join(ROOT, d)));

  it("are not imported from components/", () => {
    const offenders = files
      .filter((f) => f.startsWith(path.join(ROOT, "components")))
      .filter((f) => importsOf(f, fs.readFileSync(f, "utf8")).some((i) => SERVER_ONLY.includes(i)));
    expect(offenders).toEqual([]);
  });

  it('are not imported from any "use client" file', () => {
    const offenders = files.filter((f) => {
      const text = fs.readFileSync(f, "utf8");
      if (!/^\s*(\/\/.*\n|\/\*[\s\S]*?\*\/\s*)*["']use client["']/.test(text)) return false;
      return importsOf(f, text).some((i) => SERVER_ONLY.includes(i));
    });
    expect(offenders).toEqual([]);
  });

  it("the scan sees the real server modules", () => {
    // Guards against a regex that silently matches nothing.
    const page = fs.readFileSync(path.join(ROOT, "app/flashcards/page.tsx"), "utf8");
    expect(importsOf(path.join(ROOT, "app/flashcards/page.tsx"), page)).toContain(
      path.join(ROOT, "lib/flashcards"),
    );
  });
});
