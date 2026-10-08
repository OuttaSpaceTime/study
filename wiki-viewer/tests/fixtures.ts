import type { Card, PageMeta } from "@/lib/types";

export function makeCard(overrides: Partial<Card> = {}): Card {
  return {
    id: "c1",
    deck: "Software Engineering",
    front: "What is a <code>cookie</code>?",
    back: "A key-value pair stored by the browser.",
    tags: ["Web"],
    due: "2026-08-10",
    stability: 12.5,
    difficulty: 5,
    reps: 3,
    lapses: 0,
    state: "review",
    interval: 12,
    lastReview: "2026-07-29",
    suspended: false,
    ...overrides,
  };
}

export function makePage(
  pagePath: string,
  overrides: Partial<PageMeta> = {},
): PageMeta {
  const parts = pagePath.split("/");
  const slug = parts[parts.length - 1] ?? pagePath;
  return {
    path: pagePath,
    folder: parts.slice(0, -1).join("/"),
    slug,
    title: slug,
    aliases: [],
    tags: [],
    created: "2026-01-01",
    updated: "2026-01-02",
    flashcardIds: [],
    sections: [],
    outbound: [],
    inbound: [],
    ...overrides,
  };
}
