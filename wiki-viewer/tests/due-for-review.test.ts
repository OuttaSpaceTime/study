import { describe, expect, it } from "vitest";
import { dueForReview } from "@/app/lib";
import type { PageMeta } from "@/lib/types";

function makePage(
  pagePath: string,
  nextReview: string,
  tags: string[] = [],
): PageMeta {
  const parts = pagePath.split("/");
  const slug = parts[parts.length - 1] ?? pagePath;
  return {
    path: pagePath,
    folder: parts.slice(0, -1).join("/"),
    slug,
    title: slug,
    aliases: [],
    tags,
    created: "2026-01-01",
    updated: "2026-01-02",
    nextReview,
    reviewInterval: null,
    depth: null,
    isIndex: false,
    sections: [],
    outbound: [],
    inbound: [],
  };
}

const TODAY = "2026-07-21";

describe("dueForReview", () => {
  it("includes pages whose next_review is today or earlier", () => {
    const pages = [
      makePage("rails/foreign-keys", "2026-07-07"),
      makePage("json-api/document-structure", TODAY),
    ];
    expect(dueForReview(pages, TODAY).map((p) => p.path)).toEqual([
      "rails/foreign-keys",
      "json-api/document-structure",
    ]);
  });

  it("excludes pages scheduled after today", () => {
    const pages = [makePage("rails/foreign-keys", "2026-07-22")];
    expect(dueForReview(pages, TODAY)).toEqual([]);
  });

  it("excludes pages with no next_review (empty string)", () => {
    const pages = [makePage("rails/rails-index", "")];
    expect(dueForReview(pages, TODAY)).toEqual([]);
  });

  it("excludes no-study pages even when overdue (mirrors get_due_entries)", () => {
    const pages = [
      makePage("rails/foreign-keys", "2026-07-07"),
      makePage("llm/kv-cache", "2026-07-03", ["llm", "no-study"]),
      makePage("sql/array-agg", "2026-07-15", ["sql", "no-study"]),
    ];
    expect(dueForReview(pages, TODAY).map((p) => p.path)).toEqual([
      "rails/foreign-keys",
    ]);
  });

  it("sorts due pages by next_review ascending (most overdue first)", () => {
    const pages = [
      makePage("c", "2026-07-15"),
      makePage("a", "2026-07-05"),
      makePage("b", "2026-07-10"),
    ];
    expect(dueForReview(pages, TODAY).map((p) => p.path)).toEqual([
      "a",
      "b",
      "c",
    ]);
  });
});
