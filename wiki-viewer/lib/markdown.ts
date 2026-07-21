// Markdown helpers for article rendering: heading slugs, wikilink resolution,
// and a remark plugin that converts Obsidian wikilinks into regular links.
//
// The plugin operates on the mdast tree and only ever touches `text` nodes —
// fenced code blocks (`code`) and inline code (`inlineCode`) are distinct node
// types and are skipped explicitly, so wikilink syntax inside code is never
// rewritten.

import type { Blockquote, Parent, PhrasingContent, Root, Text } from "mdast";
import type { PageMeta } from "./types";

/**
 * Slugify a heading for anchor ids. Lowercase, alphanumerics and hyphens only.
 * Used both for `id=` on rendered h2/h3 and for `[[path#Heading]]` anchors so
 * the two always agree.
 */
export function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/[\s-]+/g, "-");
}

export type WikilinkResolver = (target: string) => string | null;

/** MOC ghost reference: the index page's path and the folder it stands for. */
export interface MocRef {
  path: string;
  folder: string;
}

/**
 * Build a resolver from the page index. Mirrors lib/wiki.ts resolution:
 * exact path match first, then unique slug (last path segment) match.
 * MOC (*-index) pages aren't rendered — wikilinks targeting one resolve to
 * its folder view instead.
 */
export function createWikilinkResolver(
  pages: readonly PageMeta[],
  mocs: readonly MocRef[] = [],
): WikilinkResolver {
  const byPath = new Set(pages.map((p) => p.path));
  const bySlug = new Map<string, string[]>();
  for (const p of pages) {
    const list = bySlug.get(p.slug) ?? [];
    list.push(p.path);
    bySlug.set(p.slug, list);
  }
  const mocByPath = new Map(mocs.map((m) => [m.path, m.folder]));
  const mocBySlug = new Map<string, string[]>();
  for (const m of mocs) {
    const slug = m.path.split("/").pop() ?? m.path;
    const list = mocBySlug.get(slug) ?? [];
    list.push(m.folder);
    mocBySlug.set(slug, list);
  }
  return (target) => {
    if (byPath.has(target)) return target;
    const mocFolder = mocByPath.get(target);
    if (mocFolder !== undefined) return mocFolder || null;
    // Bare names resolve by slug like in Obsidian; a path-qualified target
    // that doesn't match exactly is broken, never folder-corrected.
    if (target.includes("/")) return null;
    const candidates = bySlug.get(target);
    if (candidates && candidates.length === 1) return candidates[0] ?? null;
    if (!candidates?.length) {
      const folders = mocBySlug.get(target);
      if (folders && folders.length === 1) return folders[0] || null;
    }
    return null;
  };
}

/**
 * Wiki pages carry their own `# Title` as the first line; the article header
 * already renders the title, so drop a leading H1 to avoid doubling it.
 */
export function stripLeadingH1(markdown: string): string {
  return markdown.replace(/^\s*#[ \t][^\n]*\n?/, "").replace(/^\n+/, "");
}

// Callout markers: a blockquote whose first line opens with `[Note]`,
// `[Warning]`, `[Heuristic]`, etc. The label is lifted into a title row and
// the marker text is stripped from the body.
const CALLOUT_PATTERN = /^\[([A-Za-z][\w-]*)\]\s*/;

/**
 * Remark plugin: turn `> [Label] text` blockquotes into styled callouts.
 * Strips the `[Label]` marker from the body, prepends a `.callout-title`
 * paragraph carrying the label, and tags the blockquote with
 * `callout callout-<type>` classes for globals.css to style.
 */
export function remarkCallouts() {
  return function transform(tree: Root): void {
    visitBlockquotes(tree);
  };
}

function visitBlockquotes(node: Parent): void {
  for (const child of node.children) {
    if (child.type === "blockquote") applyCallout(child);
    if ("children" in child) visitBlockquotes(child);
  }
}

function applyCallout(quote: Blockquote): void {
  const firstParagraph = quote.children[0];
  if (!firstParagraph || firstParagraph.type !== "paragraph") return;
  const firstText = firstParagraph.children[0];
  if (!firstText || firstText.type !== "text") return;
  const match = CALLOUT_PATTERN.exec(firstText.value);
  if (!match) return;

  const label = match[1] ?? "";
  const type = label.toLowerCase();
  firstText.value = firstText.value.slice(match[0].length);
  quote.children.unshift({
    type: "paragraph",
    children: [{ type: "text", value: label }],
    data: { hProperties: { className: "callout-title" } },
  });
  quote.data = {
    ...quote.data,
    hProperties: {
      ...(quote.data?.hProperties ?? {}),
      className: ["callout", `callout-${type}`],
    },
  };
}

const WIKILINK_PATTERN = /(!?)\[\[([^[\]]+)\]\]/g;

export interface RemarkWikilinksOptions {
  resolve: WikilinkResolver;
}

/**
 * Remark plugin: convert `[[path]]`, `[[path|display]]`, `[[path#Heading]]`,
 * `[[path#Heading|display]]` text into links. Resolved targets become
 * `/wiki/<path>` links with className "wikilink"; unresolved targets become
 * `<span class="wikilink-broken">` with the display text. Embeds `![[...]]`
 * are left as literal text.
 */
export function remarkWikilinks(options: RemarkWikilinksOptions) {
  return function transform(tree: Root): void {
    visitParent(tree, options.resolve);
  };
}

function visitParent(node: Parent, resolve: WikilinkResolver): void {
  // Iterate backwards so splicing replacements in does not shift later indices.
  for (let i = node.children.length - 1; i >= 0; i--) {
    const child = node.children[i];
    if (!child || child.type === "code" || child.type === "inlineCode") continue;
    if (child.type === "text") {
      const replacement = convertTextNode(child, resolve);
      if (replacement) node.children.splice(i, 1, ...replacement);
    } else if ("children" in child) {
      visitParent(child, resolve);
    }
  }
}

/** Returns replacement nodes, or null if the text contains no wikilinks. */
function convertTextNode(
  node: Text,
  resolve: WikilinkResolver,
): PhrasingContent[] | null {
  const value = node.value;
  const out: PhrasingContent[] = [];
  let last = 0;
  let converted = false;
  WIKILINK_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = WIKILINK_PATTERN.exec(value)) !== null) {
    const [full = "", bang, inner] = match;
    // Embeds stay literal: don't advance `last`, the text is kept verbatim.
    // (`inner` is never empty in practice — the capture group requires it.)
    if (bang === "!" || !inner) continue;
    if (match.index > last) {
      out.push({ type: "text", value: value.slice(last, match.index) });
    }
    out.push(wikilinkNode(inner, resolve));
    last = match.index + full.length;
    converted = true;
  }
  if (!converted) return null;
  if (last < value.length) {
    out.push({ type: "text", value: value.slice(last) });
  }
  return out;
}

function wikilinkNode(
  inner: string,
  resolve: WikilinkResolver,
): PhrasingContent {
  const [targetPart = "", ...displayParts] = inner.split("|");
  const display = displayParts.join("|").trim();
  const [pathPart = "", ...headingParts] = targetPart.split("#");
  const heading = headingParts.join("#").trim();
  const target = pathPart.trim();
  const label = display || (heading ? `${target}#${heading}` : target) || inner;

  // Same-page anchor: [[#Heading]].
  if (!target && heading) {
    return wikiAnchor(`#${slugifyHeading(heading)}`, label);
  }

  const resolved = target ? resolve(target) : null;
  if (!resolved) {
    // Custom node type; mdast-util-to-hast's unknown handler plus
    // data.hName/hProperties turn it into <span class="wikilink-broken">.
    const broken = {
      type: "wikilinkBroken",
      children: [{ type: "text", value: label }],
      data: {
        hName: "span",
        hProperties: { className: "wikilink-broken" },
      },
    };
    return broken as unknown as PhrasingContent;
  }

  const url = heading
    ? `/wiki/${resolved}#${slugifyHeading(heading)}`
    : `/wiki/${resolved}`;
  return wikiAnchor(url, label);
}

function wikiAnchor(url: string, label: string): PhrasingContent {
  return {
    type: "link",
    url,
    children: [{ type: "text", value: label }],
    data: { hProperties: { className: "wikilink" } },
  };
}
