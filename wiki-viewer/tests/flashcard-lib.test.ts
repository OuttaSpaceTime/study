import { describe, expect, it } from "vitest";
import {
  filterCards,
  searchableText,
  stateCounts,
  stateOf,
  tagCounts,
} from "@/components/flashcards/lib";
import { makeCard } from "./fixtures";

const NO_FILTERS = { query: "", state: null, tag: null, deck: null };

describe("stateOf", () => {
  it("reports the scheduling state", () => {
    expect(stateOf(makeCard({ state: "relearning" }))).toBe("relearning");
  });

  it("reports suspended regardless of scheduling state", () => {
    expect(stateOf(makeCard({ state: "review", suspended: true }))).toBe(
      "suspended",
    );
  });
});

describe("searchableText", () => {
  it("strips HTML tags so markup never matches a query", () => {
    expect(searchableText(makeCard())).not.toContain("<code>");
    expect(searchableText(makeCard())).toContain("cookie");
  });

  it("includes tags and lowercases everything", () => {
    expect(searchableText(makeCard({ tags: ["Security"] }))).toContain("security");
  });
});

describe("filterCards", () => {
  const cards = [
    makeCard({ id: "a", front: "cookies", tags: ["Web"], state: "review" }),
    makeCard({ id: "b", front: "indexes", tags: ["SQL"], state: "new" }),
    makeCard({ id: "c", front: "joins", tags: ["SQL"], suspended: true }),
    makeCard({ id: "d", front: "vacuum", deck: "Personal", tags: ["SQL"] }),
  ];

  it("returns everything when no filter is set", () => {
    expect(filterCards(cards, NO_FILTERS)).toHaveLength(4);
  });

  it("filters by state, treating suspended as its own state", () => {
    expect(
      filterCards(cards, { ...NO_FILTERS, state: "suspended" }).map((c) => c.id),
    ).toEqual(["c"]);
  });

  it("filters by tag", () => {
    expect(
      filterCards(cards, { ...NO_FILTERS, tag: "SQL" }).map((c) => c.id),
    ).toEqual(["b", "c", "d"]);
  });

  it("filters by deck", () => {
    expect(
      filterCards(cards, { ...NO_FILTERS, deck: "Personal" }).map((c) => c.id),
    ).toEqual(["d"]);
  });

  it("matches the query case-insensitively against card text", () => {
    expect(
      filterCards(cards, { ...NO_FILTERS, query: "JOIN" }).map((c) => c.id),
    ).toEqual(["c"]);
  });

  it("combines filters conjunctively", () => {
    expect(
      filterCards(cards, { ...NO_FILTERS, tag: "SQL", state: "new" }).map(
        (c) => c.id,
      ),
    ).toEqual(["b"]);
  });
});

describe("tagCounts", () => {
  it("counts tags and orders by frequency, then alphabetically", () => {
    const cards = [
      makeCard({ tags: ["SQL", "Web"] }),
      makeCard({ tags: ["SQL"] }),
      makeCard({ tags: ["Auth"] }),
    ];
    expect(tagCounts(cards)).toEqual([
      { tag: "SQL", count: 2 },
      { tag: "Auth", count: 1 },
      { tag: "Web", count: 1 },
    ]);
  });
});

describe("stateCounts", () => {
  it("orders states by lifecycle and omits empty ones", () => {
    const cards = [
      makeCard({ state: "review" }),
      makeCard({ state: "new" }),
      makeCard({ state: "review" }),
    ];
    expect(stateCounts(cards)).toEqual([
      { state: "new", count: 1 },
      { state: "review", count: 2 },
    ]);
  });

  it("counts suspended cards separately from their scheduling state", () => {
    const cards = [makeCard({ state: "review", suspended: true })];
    expect(stateCounts(cards)).toEqual([{ state: "suspended", count: 1 }]);
  });
});
