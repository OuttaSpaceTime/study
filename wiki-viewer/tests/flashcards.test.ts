// The mapping layer over the deck client. The deck itself is mocked with
// records shaped like agentic-spaced-repetition's app-server `cardRecords` rows (ISO UTC
// datetimes, tags as a list, state as a number), so what is tested is the
// viewer's own behaviour: state names, local calendar days, tag filtering.
import { beforeEach, describe, expect, it, vi } from "vitest";

const deckCall = vi.fn();
vi.mock("@/lib/deck-client", () => ({ deckCall: (...args: unknown[]) => deckCall(...args) }));

import {
  getAllCards,
  getCardsByIds,
  getCardsByTags,
  getDeckOverview,
  getRecentlyStudied,
} from "@/lib/flashcards";

const DAY_MS = 86_400_000;

/** Local-midday-anchored timestamp, so a local-day bucket is unambiguous. */
function daysAgo(n: number): number {
  const d = new Date();
  d.setHours(12, 0, 0, 0);
  return d.getTime() - n * DAY_MS;
}

function localDay(ms: number): string {
  const d = new Date(ms);
  const month = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${String(d.getDate()).padStart(2, "0")}`;
}

function iso(ms: number): string {
  return new Date(ms).toISOString();
}

function record(overrides: Record<string, unknown>) {
  return {
    id: "x",
    deckId: "d1",
    deck: "Software Engineering",
    front: "front",
    back: "back",
    tags: [] as string[],
    type: "guided",
    exercise: null,
    suspended: false,
    due: iso(daysAgo(1)),
    stability: 10,
    difficulty: 5,
    reps: 2,
    lapses: 0,
    state: 2,
    lastReview: null as string | null,
    interval: 12,
    inheritedFrom: null,
    createdAt: iso(daysAgo(1)),
    updatedAt: iso(daysAgo(1)),
    ...overrides,
  };
}

// Newest first, as the server returns them.
const RECORDS = [
  record({ id: "new-int", deck: "Personal", front: "newest", state: 0, reps: 0 }),
  record({ id: "susp", front: "suspended one", tags: ["SQL"], suspended: true, due: iso(daysAgo(5)) }),
  record({
    id: "mid-text",
    front: "middle",
    tags: ["SQL", "Web"],
    lapses: 7,
    due: iso(daysAgo(40)),
    lastReview: iso(daysAgo(2)),
  }),
  record({ id: "old-int", front: "oldest", tags: ["Web"], reps: 3, due: iso(daysAgo(90)) }),
];

beforeEach(() => {
  deckCall.mockReset();
  deckCall.mockImplementation(async (method: string, params?: { ids?: string[] }) => {
    if (method === "cardRecords") {
      return params?.ids ? RECORDS.filter((r) => params.ids!.includes(r.id)) : RECORDS;
    }
    throw new Error(`unexpected method ${method}`);
  });
});

describe("getAllCards", () => {
  it("keeps the server's newest-first order", async () => {
    expect((await getAllCards()).map((c) => c.id)).toEqual(["new-int", "susp", "mid-text", "old-int"]);
  });

  it("maps records onto the Card shape", async () => {
    const card = (await getAllCards()).find((c) => c.id === "mid-text");
    expect(card).toMatchObject({
      deck: "Software Engineering",
      tags: ["SQL", "Web"],
      state: "review",
      lapses: 7,
      suspended: false,
    });
  });

  it("names every FSRS state and falls back to new for an unknown one", async () => {
    deckCall.mockResolvedValueOnce(
      [0, 1, 2, 3, 9].map((state) => record({ id: `s${state}`, state })),
    );
    expect((await getAllCards()).map((c) => c.state)).toEqual([
      "new",
      "learning",
      "review",
      "relearning",
      "new",
    ]);
  });

  it("renders dates as local calendar days", async () => {
    const card = (await getAllCards()).find((c) => c.id === "mid-text");
    expect(card?.due).toBe(localDay(daysAgo(40)));
    expect(card?.lastReview).toBe(localDay(daysAgo(2)));
  });

  it("takes the local day, not the UTC day, of an instant near UTC midnight", async () => {
    const instant = "2026-03-14T23:30:00.000Z";
    const previousTz = process.env.TZ;
    try {
      // Auckland is UTC+13 in March: already the 15th. Los Angeles is still the 14th.
      for (const [tz, day] of [
        ["Pacific/Auckland", "2026-03-15"],
        ["America/Los_Angeles", "2026-03-14"],
      ] as const) {
        process.env.TZ = tz;
        deckCall.mockResolvedValueOnce([record({ id: "late", due: instant, lastReview: instant })]);
        const [card] = await getAllCards();
        expect(card?.due, tz).toBe(day);
        expect(card?.lastReview, tz).toBe(day);
      }
    } finally {
      if (previousTz === undefined) delete process.env.TZ;
      else process.env.TZ = previousTz;
    }
  });

  it("keeps lastReview null when the card was never reviewed", async () => {
    expect((await getAllCards()).find((c) => c.id === "new-int")?.lastReview).toBeNull();
  });

  it("reads an empty tag list as no tags", async () => {
    expect((await getAllCards()).find((c) => c.id === "new-int")?.tags).toEqual([]);
  });

  it("marks suspended cards", async () => {
    expect((await getAllCards()).find((c) => c.id === "susp")?.suspended).toBe(true);
  });
});

describe("getCardsByIds", () => {
  it("returns cards in the order the page declared them", async () => {
    expect((await getCardsByIds(["new-int", "old-int"])).map((c) => c.id)).toEqual([
      "new-int",
      "old-int",
    ]);
    expect((await getCardsByIds(["old-int", "new-int"])).map((c) => c.id)).toEqual([
      "old-int",
      "new-int",
    ]);
  });

  it("drops ids with no matching card instead of leaving holes", async () => {
    expect((await getCardsByIds(["old-int", "deleted-card"])).map((c) => c.id)).toEqual(["old-int"]);
  });

  it("asks the deck for nothing when the id list is empty", async () => {
    expect(await getCardsByIds([])).toEqual([]);
    expect(deckCall).not.toHaveBeenCalled();
  });
});

describe("getCardsByTags", () => {
  it("matches tags case-insensitively", async () => {
    expect((await getCardsByTags(["web"])).map((c) => c.id)).toEqual(["mid-text", "old-int"]);
  });

  it("returns nothing when the page has no tags", async () => {
    expect(await getCardsByTags([])).toEqual([]);
  });

  it("caps the match at 12 cards", async () => {
    deckCall.mockResolvedValueOnce(
      Array.from({ length: 20 }, (_, i) => record({ id: `c${i}`, tags: ["Web"] })),
    );
    expect(await getCardsByTags(["web"])).toHaveLength(12);
  });
});

describe("getDeckOverview", () => {
  it("passes the server's counts through", async () => {
    const overview = {
      total: 3,
      deckCount: 2,
      states: [
        { label: "new", count: 1 },
        { label: "learning", count: 0 },
        { label: "review", count: 2 },
        { label: "relearning", count: 0 },
      ],
    };
    deckCall.mockResolvedValueOnce(overview);
    expect(await getDeckOverview()).toEqual(overview);
    expect(deckCall).toHaveBeenCalledWith("deckOverview");
  });
});

describe("getRecentlyStudied", () => {
  it("passes the limit and returns the server's card-and-day pairs", async () => {
    const rows = [{ id: "old-int", at: localDay(daysAgo(1)) }];
    deckCall.mockResolvedValueOnce(rows);
    expect(await getRecentlyStudied(2)).toEqual(rows);
    expect(deckCall).toHaveBeenCalledWith("recentlyStudied", { limit: 2 });
  });

  it("asks for 100 reviews by default", async () => {
    deckCall.mockResolvedValueOnce([]);
    await getRecentlyStudied();
    expect(deckCall).toHaveBeenCalledWith("recentlyStudied", { limit: 100 });
  });
});

describe("when the deck cannot be read", () => {
  beforeEach(() => {
    deckCall.mockRejectedValue(new Error("deck server exited"));
  });

  it("reports no overview instead of throwing", async () => {
    expect(await getDeckOverview()).toBeNull();
  });

  it("reports no recent study instead of throwing", async () => {
    expect(await getRecentlyStudied()).toEqual([]);
  });
});
