import { describe, expect, it } from "vitest";
import { recentlyStudiedPages } from "@/app/lib";
import { makePage } from "./fixtures";

describe("recentlyStudiedPages", () => {
  it("keeps only pages whose cards were studied", () => {
    const pages = [
      makePage("rails/foreign-keys", { flashcardIds: ["a"] }),
      makePage("security/hsts", { flashcardIds: ["untouched"] }),
      makePage("rails/rails-index", { flashcardIds: [] }),
    ];
    const result = recentlyStudiedPages(pages, [{ id: "a", at: "2026-07-30" }]);
    expect(result.map((r) => r.page.path)).toEqual(["rails/foreign-keys"]);
  });

  it("counts how many of the recent cards each page covers", () => {
    const pages = [makePage("sql/joins", { flashcardIds: ["a", "b", "c"] })];
    const result = recentlyStudiedPages(pages, [
      { id: "a", at: "2026-07-30" },
      { id: "b", at: "2026-07-29" },
    ]);
    expect(result[0]?.cards).toBe(2);
  });

  it("reports the most recent review date touching the page", () => {
    const pages = [makePage("sql/joins", { flashcardIds: ["a", "b"] })];
    const result = recentlyStudiedPages(pages, [
      { id: "a", at: "2026-07-20" },
      { id: "b", at: "2026-07-31" },
    ]);
    expect(result[0]?.lastStudied).toBe("2026-07-31");
  });

  it("ranks by recency first", () => {
    const pages = [
      makePage("old/page", { flashcardIds: ["a", "b", "c"] }),
      makePage("new/page", { flashcardIds: ["d"] }),
    ];
    const result = recentlyStudiedPages(pages, [
      { id: "a", at: "2026-07-01" },
      { id: "b", at: "2026-07-02" },
      { id: "c", at: "2026-07-03" },
      { id: "d", at: "2026-07-31" },
    ]);
    expect(result.map((r) => r.page.path)).toEqual(["new/page", "old/page"]);
  });

  it("breaks ties on the same date by card count", () => {
    const pages = [
      makePage("few/page", { flashcardIds: ["a"] }),
      makePage("many/page", { flashcardIds: ["b", "c"] }),
    ];
    const result = recentlyStudiedPages(pages, [
      { id: "a", at: "2026-07-31" },
      { id: "b", at: "2026-07-31" },
      { id: "c", at: "2026-07-31" },
    ]);
    expect(result.map((r) => r.page.path)).toEqual(["many/page", "few/page"]);
  });

  it("caps the list at the requested limit", () => {
    const pages = Array.from({ length: 12 }, (_, i) =>
      makePage(`topic/page-${i}`, { flashcardIds: [`card-${i}`] }),
    );
    const studied = pages.map((_page, i) => ({
      id: `card-${i}`,
      at: `2026-07-${String(i + 1).padStart(2, "0")}`,
    }));
    expect(recentlyStudiedPages(pages, studied, 3)).toHaveLength(3);
  });

  it("returns nothing when there are no recent reviews", () => {
    expect(recentlyStudiedPages([makePage("a/b", { flashcardIds: ["x"] })], [])).toEqual([]);
  });
});
