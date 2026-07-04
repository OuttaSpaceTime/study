// Shared contract between the server data layer (lib/wiki.ts) and all client components.

export interface PageMeta {
  /** Wiki-relative path without extension, e.g. "rails/foreign-keys" or "rails/routing/scope-vs-namespace". */
  path: string;
  /** Folder portion of path, e.g. "rails" or "rails/routing". */
  folder: string;
  /** Filename without extension, e.g. "foreign-keys". */
  slug: string;
  title: string;
  aliases: string[];
  tags: string[];
  created: string;
  updated: string;
  /** ISO date or "" (index/MOC pages have none). */
  nextReview: string;
  reviewInterval: number | null;
  depth: number | null;
  /** True for *-index.md MOC pages. */
  isIndex: boolean;
  /** Resolved wiki paths this page links to. */
  outbound: string[];
  /** Wiki paths that link to this page. */
  inbound: string[];
}

export interface TreeFolder {
  /** Display name, e.g. "rails". Root is "wiki". */
  name: string;
  /** Folder path, e.g. "rails/routing". Root is "". */
  path: string;
  folders: TreeFolder[];
  /** Pages directly in this folder; index page first, then by title. */
  pages: PageMeta[];
}

export interface GraphNode {
  id: string; // page path
  title: string;
  folder: string;
  isIndex: boolean;
  /** Total degree (inbound + outbound), for node sizing. */
  linkCount: number;
}

export interface GraphLink {
  source: string;
  target: string;
}

export interface WikiIndexPayload {
  pages: PageMeta[];
  tree: TreeFolder;
  graph: { nodes: GraphNode[]; links: GraphLink[] };
  generatedAt: string;
}

export interface WikiPage {
  meta: PageMeta;
  /** Raw markdown body, frontmatter stripped. Wikilinks are NOT yet converted. */
  markdown: string;
}
