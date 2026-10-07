// Server-only data layer for the SRS deck. Reads flashcard-mcp's SQLite file
// directly (read-only) rather than going through the MCP server, so the viewer
// stays a plain Next app with no extra process to run.
import { DatabaseSync } from "node:sqlite";
import { masterDbPath } from "./flashcard-path";
import type { Card, CardState, DeckOverview } from "./types";

export const MASTER_DB = masterDbPath();

// ts-fsrs State enum, mirrored from flashcard-mcp's schema (Card.state).
const STATE_NAMES: CardState[] = ["new", "learning", "review", "relearning"];

let db: DatabaseSync | null = null;

function open(): DatabaseSync {
  // `readOnly` matters: flashcard-mcp owns writes, and an accidental viewer
  // write would corrupt review history the sync trusts as append-only.
  // `timeout` covers the EXCLUSIVE window of a concurrent writer — the file is
  // journal_mode=delete, so a review being committed locks readers out.
  if (!MASTER_DB) {
    throw new Error(
      "FLASHCARD_MCP_DIR is not set — add it to .env.local at the repo root.",
    );
  }
  db ??= new DatabaseSync(MASTER_DB, { readOnly: true, timeout: 5000 });
  return db;
}

/**
 * Local calendar day (not UTC) of a datetime column, as YYYY-MM-DD. Datetime
 * columns are uniform ISO text: flashcard-mcp converts the epoch-ms integers
 * older Prisma wrote on every start (its src/db/normalize.ts).
 */
function localDay(column: string): string {
  return `date(${column}, 'localtime')`;
}

interface CardRow {
  id: string;
  deck: string;
  front: string;
  back: string;
  tags: string;
  due: string;
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  state: number;
  interval: number;
  lastReview: string | null;
  suspended: number;
}

const CARD_SELECT = `
  SELECT c.id, d.name AS deck, c.front, c.back, c.tags,
         ${localDay("c.due")} AS due, c.stability, c.difficulty, c.reps,
         c.lapses, c.state, c.interval,
         CASE WHEN c.lastReview IS NULL THEN NULL ELSE ${localDay("c.lastReview")} END AS lastReview,
         c.suspended
  FROM Card c JOIN Deck d ON d.id = c.deckId
`;

function toCard(row: CardRow): Card {
  return {
    id: row.id,
    deck: row.deck,
    front: row.front,
    back: row.back,
    tags: row.tags ? row.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    due: row.due,
    stability: row.stability,
    difficulty: row.difficulty,
    reps: row.reps,
    lapses: row.lapses,
    state: STATE_NAMES[row.state] ?? "new",
    interval: row.interval,
    lastReview: row.lastReview,
    suspended: row.suspended === 1,
  };
}

/** Cards whose ids a wiki page declares, in the page's declared order. */
export function getCardsByIds(ids: readonly string[]): Card[] {
  if (ids.length === 0) return [];
  const placeholders = ids.map(() => "?").join(",");
  const rows = open()
    .prepare(`${CARD_SELECT} WHERE c.id IN (${placeholders})`)
    .all(...ids) as unknown as CardRow[];
  const byId = new Map(rows.map((r) => [r.id, toCard(r)]));
  return ids.map((id) => byId.get(id)).filter((c): c is Card => c !== undefined);
}

/** Every card, newest first — small enough (hundreds) to ship whole. */
export function getAllCards(): Card[] {
  const rows = open()
    .prepare(`${CARD_SELECT} ORDER BY c.createdAt DESC`)
    .all() as unknown as CardRow[];
  return rows.map(toCard);
}

/** Cards sharing any tag with the page, for pages that declare no card ids. */
export function getCardsByTags(tags: readonly string[]): Card[] {
  if (tags.length === 0) return [];
  const lowered = tags.map((t) => t.toLowerCase());
  return getAllCards()
    .filter((card) => card.tags.some((t) => lowered.includes(t.toLowerCase())))
    .slice(0, 12);
}

/**
 * Headline counts for the dashboard tile, or null when the deck can't be read.
 * The wiki is the product here; a missing or locked master.db must not take the
 * front page down with it.
 */
export function getDeckOverview(): DeckOverview | null {
  try {
    const byState = open()
      .prepare(
        `SELECT state, COUNT(*) AS n FROM Card WHERE suspended = 0 GROUP BY state`,
      )
      .all() as unknown as { state: number; n: number }[];
    const totals = open()
      .prepare(
        `SELECT COUNT(*) AS total, COUNT(DISTINCT deckId) AS decks
         FROM Card WHERE suspended = 0`,
      )
      .get() as unknown as { total: number; decks: number };

    const counts = new Map(byState.map((r) => [STATE_NAMES[r.state] ?? "new", r.n]));
    return {
      total: totals.total,
      deckCount: totals.decks,
      states: STATE_NAMES.map((label) => ({ label, count: counts.get(label) ?? 0 })),
    };
  } catch {
    return null;
  }
}

/**
 * Card ids from the most recent `limit` reviews, newest first, deduplicated —
 * the "what have I actually been studying" signal the dashboard ranks pages by.
 */
export function getRecentlyStudied(limit = 100): { id: string; at: string }[] {
  try {
    return recentlyStudiedRows(limit);
  } catch {
    return [];
  }
}

function recentlyStudiedRows(limit: number): { id: string; at: string }[] {
  const rows = open()
    .prepare(
      `SELECT cardId, ${localDay("reviewedAt")} AS at FROM Review ORDER BY reviewedAt DESC LIMIT ?`,
    )
    .all(limit) as unknown as { cardId: string; at: string }[];
  // Newest first, so the first row seen for a card is its latest review.
  const latest = new Map<string, string>();
  for (const row of rows) if (!latest.has(row.cardId)) latest.set(row.cardId, row.at);
  return [...latest].map(([id, at]) => ({ id, at }));
}
