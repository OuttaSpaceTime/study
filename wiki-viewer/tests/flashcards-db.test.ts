// Exercises the SQL layer against a real fixture database. Datetimes are ISO
// text, as flashcard-mcp leaves them (it converts older epoch-ms integers on
// every start, src/db/normalize.ts, and tests that conversion there).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

let dbPath: string;
type Flashcards = typeof import("@/lib/flashcards");

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

function isoOf(ms: number): string {
  return new Date(ms).toISOString().replace("Z", "+00:00");
}

async function load(): Promise<Flashcards> {
  vi.resetModules();
  process.env["FLASHCARD_DB"] = dbPath;
  return import("@/lib/flashcards");
}

beforeAll(() => {
  dbPath = path.join(
    fs.mkdtempSync(path.join(os.tmpdir(), "flashcards-test-")),
    "master.db",
  );
  const db = new DatabaseSync(dbPath);
  db.exec(`
    CREATE TABLE Deck (id TEXT PRIMARY KEY, name TEXT);
    CREATE TABLE Card (
      id TEXT PRIMARY KEY, deckId TEXT, front TEXT, back TEXT, tags TEXT,
      due, stability REAL, difficulty REAL, reps INTEGER, lapses INTEGER,
      state INTEGER, interval REAL, lastReview, suspended INTEGER, createdAt
    );
    CREATE TABLE Review (cardId TEXT, rating INTEGER, reviewedAt, elapsedDays REAL);
    INSERT INTO Deck VALUES ('d1', 'Software Engineering'), ('d2', 'Personal');
  `);

  const card = db.prepare(
    `INSERT INTO Card VALUES (?, ?, ?, ?, ?, ?, 10.0, 5.0, ?, ?, ?, 12.0, ?, ?, ?)`,
  );
  card.run("old-int", "d1", "oldest", "back", "Web", isoOf(daysAgo(90)), 3, 0, 2, null, 0, isoOf(daysAgo(90)));
  card.run("mid-text", "d1", "middle", "back", "SQL,Web", isoOf(daysAgo(40)), 5, 7, 2, isoOf(daysAgo(2)), 0, isoOf(daysAgo(40)));
  card.run("new-int", "d2", "newest", "back", "", isoOf(daysAgo(1)), 0, 0, 0, null, 0, isoOf(daysAgo(1)));
  card.run("susp", "d1", "suspended one", "back", "SQL", isoOf(daysAgo(5)), 1, 0, 2, null, 1, isoOf(daysAgo(5)));

  const review = db.prepare(`INSERT INTO Review VALUES (?, ?, ?, ?)`);
  review.run("old-int", 3, isoOf(daysAgo(1)), 5.0);
  review.run("old-int", 1, isoOf(daysAgo(1) + 3600_000), 0.1);
  review.run("mid-text", 3, isoOf(daysAgo(10)), 4.0);
  review.run("susp", 4, isoOf(daysAgo(20)), 9.0);
  db.close();
});

afterAll(() => {
  delete process.env["FLASHCARD_DB"];
});

describe("getRecentlyStudied", () => {
  it("orders by real time, newest first", async () => {
    const { getRecentlyStudied } = await load();
    expect(getRecentlyStudied().map((r) => r.id)).toEqual([
      "old-int",
      "mid-text",
      "susp",
    ]);
  });

  it("collapses repeat reviews of one card to its latest local day", async () => {
    const { getRecentlyStudied } = await load();
    const hits = getRecentlyStudied().filter((r) => r.id === "old-int");
    expect(hits).toHaveLength(1);
    expect(hits[0]?.at).toBe(localDay(daysAgo(1)));
  });

  it("counts the limit in reviews, so it can return fewer cards", async () => {
    const { getRecentlyStudied } = await load();
    // The two newest reviews are both old-int, so a limit of 2 yields 1 card.
    expect(getRecentlyStudied(2)).toEqual([
      { id: "old-int", at: localDay(daysAgo(1)) },
    ]);
  });
});

describe("getAllCards", () => {
  it("orders by creation, newest first", async () => {
    const { getAllCards } = await load();
    expect(getAllCards().map((c) => c.id)).toEqual([
      "new-int",
      "susp",
      "mid-text",
      "old-int",
    ]);
  });

  it("maps rows onto the Card shape", async () => {
    const { getAllCards } = await load();
    const card = getAllCards().find((c) => c.id === "mid-text");
    expect(card).toMatchObject({
      deck: "Software Engineering",
      tags: ["SQL", "Web"],
      state: "review",
      lapses: 7,
      suspended: false,
    });
  });

  it("reads an empty tag string as no tags", async () => {
    const { getAllCards } = await load();
    expect(getAllCards().find((c) => c.id === "new-int")?.tags).toEqual([]);
  });

  it("renders dates as local calendar days", async () => {
    const { getAllCards } = await load();
    const card = getAllCards().find((c) => c.id === "mid-text");
    expect(card?.due).toBe(localDay(daysAgo(40)));
    expect(card?.lastReview).toBe(localDay(daysAgo(2)));
  });

  it("keeps lastReview null when the card was never reviewed", async () => {
    const { getAllCards } = await load();
    expect(getAllCards().find((c) => c.id === "new-int")?.lastReview).toBeNull();
  });

  it("marks suspended cards", async () => {
    const { getAllCards } = await load();
    expect(getAllCards().find((c) => c.id === "susp")?.suspended).toBe(true);
  });
});

describe("getCardsByIds", () => {
  it("returns cards in the order the page declared them", async () => {
    const { getCardsByIds } = await load();
    expect(getCardsByIds(["new-int", "old-int"]).map((c) => c.id)).toEqual([
      "new-int",
      "old-int",
    ]);
  });

  it("drops ids with no matching card instead of leaving holes", async () => {
    const { getCardsByIds } = await load();
    expect(getCardsByIds(["old-int", "deleted-card"]).map((c) => c.id)).toEqual([
      "old-int",
    ]);
  });

  it("queries nothing for an empty id list", async () => {
    const { getCardsByIds } = await load();
    expect(getCardsByIds([])).toEqual([]);
  });
});

describe("getCardsByTags", () => {
  it("matches tags case-insensitively", async () => {
    const { getCardsByTags } = await load();
    expect(getCardsByTags(["web"]).map((c) => c.id)).toEqual([
      "mid-text",
      "old-int",
    ]);
  });

  it("returns nothing when the page has no tags", async () => {
    const { getCardsByTags } = await load();
    expect(getCardsByTags([])).toEqual([]);
  });
});

describe("getDeckOverview", () => {
  it("counts states and decks over unsuspended cards only", async () => {
    const { getDeckOverview } = await load();
    expect(getDeckOverview()).toEqual({
      total: 3,
      deckCount: 2,
      states: [
        { label: "new", count: 1 },
        { label: "learning", count: 0 },
        { label: "review", count: 2 },
        { label: "relearning", count: 0 },
      ],
    });
  });
});

describe("when the deck cannot be read", () => {
  it("reports no overview instead of throwing", async () => {
    vi.resetModules();
    process.env["FLASHCARD_DB"] = "/nonexistent/master.db";
    const { getDeckOverview } = await import("@/lib/flashcards");
    expect(getDeckOverview()).toBeNull();
    process.env["FLASHCARD_DB"] = dbPath;
  });

  it("reports no recent study instead of throwing", async () => {
    vi.resetModules();
    process.env["FLASHCARD_DB"] = "/nonexistent/master.db";
    const { getRecentlyStudied } = await import("@/lib/flashcards");
    expect(getRecentlyStudied()).toEqual([]);
    process.env["FLASHCARD_DB"] = dbPath;
  });
});
