// Dashboard helpers kept pure so the ranking rules are unit-testable.
import type { PageMeta } from "@/lib/types";

export interface StudiedPage {
  page: PageMeta;
  cards: number;
  lastStudied: string;
}

/**
 * Ranked by most recent review first, then by how many of the recent cards the
 * page covers — recency answers "where was I", and the count breaks ties toward
 * the page that carried the session over one that happened to share a card.
 */
export function recentlyStudiedPages(
  pages: readonly PageMeta[],
  studied: readonly { id: string; at: string }[],
  limit = 8,
): StudiedPage[] {
  const studiedAt = new Map(studied.map((s) => [s.id, s.at]));

  return pages
    .map((page) => {
      const dates = page.flashcardIds
        .map((id) => studiedAt.get(id))
        .filter((at) => at !== undefined);
      return {
        page,
        cards: dates.length,
        lastStudied: dates.reduce((latest, at) => (at > latest ? at : latest), ""),
      };
    })
    .filter((entry) => entry.cards > 0)
    .sort(
      (a, b) =>
        b.lastStudied.localeCompare(a.lastStudied) || b.cards - a.cards,
    )
    .slice(0, limit);
}
