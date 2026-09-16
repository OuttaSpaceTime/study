// Server-only data layer. Reads the wiki straight off disk on every call —
// 49 pages, so no caching layer is warranted.
import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import { REPO_ROOT } from "./flashcard-path";
import type {
  GraphLink,
  GraphNode,
  PageMeta,
  TreeFolder,
  WikiIndexPayload,
  WikiPage,
} from "./types";

// path.resolve also strips a trailing slash, which would otherwise break the
// `startsWith(WIKI_ROOT + path.sep)` guard in safeWikiFile for every page.
export const WIKI_ROOT = path.resolve(
  process.env.WIKI_ROOT ?? path.join(REPO_ROOT, "wiki"),
);

/** Non-content directories inside the wiki root. */
const SKIP_DIRS = new Set(["indexes"]);

async function walkMarkdownFiles(dir: string, rel = ""): Promise<string[]> {
  const out: string[] = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;
    const childRel = rel ? `${rel}/${entry.name}` : entry.name;
    if (entry.isDirectory()) {
      if (SKIP_DIRS.has(entry.name)) continue;
      out.push(...(await walkMarkdownFiles(path.join(dir, entry.name), childRel)));
    } else if (entry.name.endsWith(".md")) {
      out.push(childRel);
    }
  }
  return out;
}

function asDateString(value: unknown): string {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (value == null) return "";
  return String(value);
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(String);
}

function stripCode(markdown: string): string {
  return markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`[^`\n]*`/g, "");
}

/** Extract wikilink targets (path part only — no #anchor, no |alias, no ![[embeds]]). */
function extractLinkTargets(markdown: string): string[] {
  const targets: string[] = [];
  for (const m of stripCode(markdown).matchAll(/(!?)\[\[([^\]]+)\]\]/g)) {
    const inner = m[2];
    if (m[1] === "!" || !inner) continue;
    const target = ((inner.split("|")[0] ?? "").split("#")[0] ?? "").trim();
    if (target) targets.push(target);
  }
  return targets;
}

/** H2 headings in document order, skipping fenced code blocks. */
function extractSections(markdown: string): string[] {
  const sections: string[] = [];
  let inFence = false;
  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) inFence = !inFence;
    else if (!inFence) {
      const heading = /^##[ \t]+(.+?)\s*$/.exec(line);
      if (heading?.[1]) sections.push(heading[1]);
    }
  }
  return sections;
}

interface RawPage {
  meta: PageMeta;
  rawTargets: string[];
}

async function loadRawPages(): Promise<RawPage[]> {
  const files = await walkMarkdownFiles(WIKI_ROOT);
  const pages = await Promise.all(
    files.map(async (file): Promise<RawPage> => {
      const raw = await fs.readFile(path.join(WIKI_ROOT, file), "utf8");
      const { data, content } = matter(raw);
      const pagePath = file.replace(/\.md$/, "");
      const slug = pagePath.split("/").pop() ?? pagePath;
      const folder = pagePath.split("/").slice(0, -1).join("/");
      const meta: PageMeta = {
        path: pagePath,
        folder,
        slug,
        title: typeof data.title === "string" && data.title ? data.title : slug,
        aliases: asStringArray(data.aliases),
        tags: asStringArray(data.tags),
        created: asDateString(data.created),
        updated: asDateString(data.updated),
        flashcardIds: asStringArray(data.flashcard_ids),
        isIndex: slug.endsWith("-index"),
        sections: extractSections(content),
        outbound: [],
        inbound: [],
      };
      return { meta, rawTargets: extractLinkTargets(content) };
    }),
  );
  return pages.sort((a, b) => a.meta.path.localeCompare(b.meta.path));
}

function resolveLinks(pages: RawPage[]): void {
  const byPath = new Map(pages.map((p) => [p.meta.path, p.meta]));
  // Obsidian resolves bare names by suffix; build slug → paths for the fallback.
  const bySlug = new Map<string, string[]>();
  for (const p of pages) {
    const list = bySlug.get(p.meta.slug) ?? [];
    list.push(p.meta.path);
    bySlug.set(p.meta.slug, list);
  }
  for (const page of pages) {
    const resolved = new Set<string>();
    for (const target of page.rawTargets) {
      let hit = byPath.has(target) ? target : undefined;
      // Bare names resolve by slug like in Obsidian; a path-qualified target
      // that doesn't match exactly is broken, never folder-corrected.
      if (!hit && !target.includes("/")) {
        const candidates = bySlug.get(target);
        if (candidates?.length === 1) hit = candidates[0];
      }
      if (hit && hit !== page.meta.path) resolved.add(hit);
    }
    page.meta.outbound = [...resolved].sort();
  }
  for (const page of pages) {
    for (const target of page.meta.outbound) {
      byPath.get(target)?.inbound.push(page.meta.path);
    }
  }
  for (const page of pages) page.meta.inbound.sort();
}

function buildTree(pages: PageMeta[]): TreeFolder {
  const root: TreeFolder = { name: "wiki", path: "", folders: [], pages: [] };
  const folders = new Map<string, TreeFolder>([["", root]]);
  const ensureFolder = (folderPath: string): TreeFolder => {
    const existing = folders.get(folderPath);
    if (existing) return existing;
    const name = folderPath.split("/").pop() ?? folderPath;
    const parent = ensureFolder(folderPath.split("/").slice(0, -1).join("/"));
    const folder: TreeFolder = { name, path: folderPath, folders: [], pages: [] };
    parent.folders.push(folder);
    folders.set(folderPath, folder);
    return folder;
  };
  for (const page of pages) ensureFolder(page.folder).pages.push(page);
  for (const folder of folders.values()) {
    folder.folders.sort((a, b) => a.name.localeCompare(b.name));
    folder.pages.sort((a, b) => {
      if (a.isIndex !== b.isIndex) return a.isIndex ? -1 : 1;
      return a.title.localeCompare(b.title);
    });
  }
  return root;
}

function buildGraph(pages: PageMeta[]): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodes = pages.map((p) => ({
    id: p.path,
    title: p.title,
    folder: p.folder,
    isIndex: p.isIndex,
    linkCount: p.inbound.length + p.outbound.length,
  }));
  const links: GraphLink[] = [];
  const seen = new Set<string>();
  for (const page of pages) {
    for (const target of page.outbound) {
      const key = [page.path, target].sort().join("→");
      if (seen.has(key)) continue;
      seen.add(key);
      links.push({ source: page.path, target });
    }
  }
  return { nodes, links };
}

async function buildWikiIndex(): Promise<WikiIndexPayload> {
  const raw = await loadRawPages();
  resolveLinks(raw);
  const all = raw.map((p) => p.meta);
  // MOC (*-index) pages aren't rendered as content — they survive only as
  // ghost hub nodes in the graph, so build it before their links are stripped.
  const graph = buildGraph(all);
  const mocPaths = new Set(all.filter((p) => p.isIndex).map((p) => p.path));
  const pages = all.filter((p) => !p.isIndex);
  for (const page of pages) {
    page.outbound = page.outbound.filter((t) => !mocPaths.has(t));
    page.inbound = page.inbound.filter((t) => !mocPaths.has(t));
  }
  return {
    pages,
    tree: buildTree(pages),
    graph,
    generatedAt: new Date().toISOString(),
  };
}

// Micro-cache: one request renders the page, its metadata, and the folder
// view from the same snapshot instead of re-reading the whole wiki each time.
// The short TTL keeps "edit file, reload, see it" intact.
const INDEX_TTL_MS = 2000;
let indexCache: { at: number; value: Promise<WikiIndexPayload> } | null = null;

export function getWikiIndex(): Promise<WikiIndexPayload> {
  if (!indexCache || Date.now() - indexCache.at >= INDEX_TTL_MS) {
    const value = buildWikiIndex();
    const entry = { at: Date.now(), value };
    indexCache = entry;
    value.catch(() => {
      // Never cache a failure (e.g. transient fs error during a wiki write).
      if (indexCache === entry) indexCache = null;
    });
  }
  return indexCache.value;
}

/** Resolve a wiki path to an absolute file path, or null if it escapes the root. */
export function safeWikiFile(wikiPath: string): string | null {
  const abs = path.resolve(WIKI_ROOT, `${wikiPath}.md`);
  if (!abs.startsWith(WIKI_ROOT + path.sep)) return null;
  return abs;
}

export async function getPage(wikiPath: string): Promise<WikiPage | null> {
  const file = safeWikiFile(wikiPath);
  if (!file) return null;
  let raw: string;
  try {
    raw = await fs.readFile(file, "utf8");
  } catch {
    return null;
  }
  const { content } = matter(raw);
  const index = await getWikiIndex();
  const meta = index.pages.find((p) => p.path === wikiPath);
  if (!meta) return null;
  return { meta, markdown: content.trim() };
}
