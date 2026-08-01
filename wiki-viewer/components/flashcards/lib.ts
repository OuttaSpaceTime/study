import type { Card, CardState } from "@/lib/types";

export type StateKey = CardState | "suspended";

export const STATE_COLORS: Record<StateKey, string> = {
  new: "#4a5fc1",
  learning: "#b4541a",
  review: "#2f7d5b",
  relearning: "#c2405a",
  suspended: "#818794",
};

export function stateOf(card: Card): StateKey {
  return card.suspended ? "suspended" : card.state;
}

export function searchableText(card: Card): string {
  return `${card.front} ${card.back} ${card.tags.join(" ")}`
    .replace(/<[^>]*>/g, " ")
    .toLowerCase();
}

export interface CardFilters {
  query: string;
  state: StateKey | null;
  tag: string | null;
  deck: string | null;
}

export function filterCards(cards: readonly Card[], filters: CardFilters): Card[] {
  const query = filters.query.trim().toLowerCase();
  return cards.filter((card) => {
    if (filters.state && stateOf(card) !== filters.state) return false;
    if (filters.deck && card.deck !== filters.deck) return false;
    if (filters.tag && !card.tags.includes(filters.tag)) return false;
    if (query && !searchableText(card).includes(query)) return false;
    return true;
  });
}

/** Tags across the deck, most frequent first. */
export function tagCounts(cards: readonly Card[]): { tag: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const card of cards) {
    for (const tag of card.tags) counts.set(tag, (counts.get(tag) ?? 0) + 1);
  }
  return [...counts]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count || a.tag.localeCompare(b.tag));
}

export function stateCounts(
  cards: readonly Card[],
): { state: StateKey; count: number }[] {
  const order: StateKey[] = ["new", "learning", "review", "relearning", "suspended"];
  const counts = new Map<StateKey, number>();
  for (const card of cards) {
    const key = stateOf(card);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return order
    .map((state) => ({ state, count: counts.get(state) ?? 0 }))
    .filter((entry) => entry.count > 0);
}
