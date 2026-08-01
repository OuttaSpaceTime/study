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
  /** SRS card ids this page covers, from frontmatter `flashcard_ids`. */
  flashcardIds: string[];
  /** True for *-index.md MOC pages. */
  isIndex: boolean;
  /** H2 headings in document order, for the sidebar mini-TOC. */
  sections: string[];
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

/** FSRS scheduling state, mirroring flashcard-mcp's numeric Card.state. */
export type CardState = "new" | "learning" | "review" | "relearning";

export interface Card {
  id: string;
  deck: string;
  /** Simple HTML, as authored for Anki. */
  front: string;
  back: string;
  tags: string[];
  /** Local calendar date (yyyy-mm-dd). */
  due: string;
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  state: CardState;
  /** Days until the next review. */
  interval: number;
  lastReview: string | null;
  suspended: boolean;
}

export interface DeckOverview {
  total: number;
  deckCount: number;
  states: { label: CardState; count: number }[];
}

/** Verdict from `scripts/study-calibration` — never recomputed here. */
export interface Calibration {
  verdict: "over-difficult" | "calibrated" | "under-difficult" | "low-signal";
  /** Within 2 points of a band edge, so one review could flip the verdict. */
  marginal: boolean;
  retention: number | null;
  reviews: number;
  passed: number;
  windowDays: number;
  reason: string;
}
