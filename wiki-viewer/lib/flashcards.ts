// Server-only data layer for the SRS deck. It reads through flashcard-mcp's app
// server (lib/deck-client.ts), which owns master.db and its schema; this file
// only reshapes the records into the viewer's Card type.
import { deckCall } from "./deck-client";
import type { Card, CardState, DeckOverview } from "./types";

// ts-fsrs State enum, mirrored from flashcard-mcp's schema (Card.state).
const STATE_NAMES: CardState[] = ["new", "learning", "review", "relearning"];

/** The fields of the app server's `cardRecords` rows the viewer reads. */
interface CardRecord {
  id: string;
  deck: string;
  front: string;
  back: string;
  tags: string[];
  /** ISO UTC datetime. */
  due: string;
  stability: number;
  difficulty: number;
  reps: number;
  lapses: number;
  state: number;
  interval: number;
  lastReview: string | null;
  suspended: boolean;
}

/** Local calendar day (not UTC) of an ISO datetime, as YYYY-MM-DD. */
function localDay(iso: string): string {
  const d = new Date(iso);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${String(d.getDate()).padStart(2, "0")}`;
}

function toCard(row: CardRecord): Card {
  return {
    id: row.id,
    deck: row.deck,
    front: row.front,
    back: row.back,
    tags: row.tags,
    due: localDay(row.due),
    stability: row.stability,
    difficulty: row.difficulty,
    reps: row.reps,
    lapses: row.lapses,
    state: STATE_NAMES[row.state] ?? "new",
    interval: row.interval,
    lastReview: row.lastReview === null ? null : localDay(row.lastReview),
    suspended: row.suspended,
  };
}

/** Cards whose ids a wiki page declares, in the page's declared order. */
export async function getCardsByIds(ids: readonly string[]): Promise<Card[]> {
  if (ids.length === 0) return [];
  const rows = await deckCall<CardRecord[]>("cardRecords", { ids });
  const byId = new Map(rows.map((r) => [r.id, toCard(r)]));
  return ids.map((id) => byId.get(id)).filter((c): c is Card => c !== undefined);
}

/** Every card, newest first — small enough (hundreds) to ship whole. */
export async function getAllCards(): Promise<Card[]> {
  const rows = await deckCall<CardRecord[]>("cardRecords");
  return rows.map(toCard);
}

/** Cards sharing any tag with the page, for pages that declare no card ids. */
export async function getCardsByTags(tags: readonly string[]): Promise<Card[]> {
  if (tags.length === 0) return [];
  const lowered = tags.map((t) => t.toLowerCase());
  return (await getAllCards())
    .filter((card) => card.tags.some((t) => lowered.includes(t.toLowerCase())))
    .slice(0, 12);
}

/**
 * Headline counts for the dashboard tile, or null when the deck can't be read.
 * The wiki is the product here; a missing or locked deck must not take the
 * front page down with it.
 */
export async function getDeckOverview(): Promise<DeckOverview | null> {
  try {
    return await deckCall<DeckOverview>("deckOverview");
  } catch {
    return null;
  }
}

/**
 * Card ids from the most recent `limit` reviews, newest first, deduplicated —
 * the "what have I actually been studying" signal the dashboard ranks pages by.
 */
export async function getRecentlyStudied(
  limit = 100,
): Promise<{ id: string; at: string }[]> {
  try {
    return await deckCall<{ id: string; at: string }[]>("recentlyStudied", { limit });
  } catch {
    return [];
  }
}
