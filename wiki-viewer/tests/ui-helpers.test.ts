import { describe, expect, it } from "vitest";
import { topicColor } from "@/lib/colors";
import { countPages, findFolder, topLevelFolder } from "@/components/sidebar/lib";
import type { PageMeta, TreeFolder } from "@/lib/types";

const HEX_COLOR = /^#[0-9a-f]{6}$/;

function makePage(pagePath: string): PageMeta {
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
    nextReview: "",
    reviewInterval: null,
    depth: null,
    isIndex: slug.endsWith("-index"),
    sections: [],
    outbound: [],
    inbound: [],
  };
}

describe("topicColor", () => {
  it("is deterministic for the same folder", () => {
    expect(topicColor("rails")).toBe(topicColor("rails"));
    expect(topicColor("security")).toBe(topicColor("security"));
  });

  it("returns a #rrggbb hex color", () => {
    for (const folder of ["rails", "security", "llm", "rails/routing", ""]) {
      expect(topicColor(folder)).toMatch(HEX_COLOR);
    }
  });

  it("uses only the top-level segment of a nested folder path", () => {
    expect(topicColor("rails/routing")).toBe(topicColor("rails"));
    expect(topicColor("rails/routing/deep")).toBe(topicColor("rails"));
  });

  it("treats the empty string as the 'wiki' topic", () => {
    expect(topicColor("")).toBe(topicColor("wiki"));
    expect(topicColor("")).toMatch(HEX_COLOR);
  });
});

describe("sidebar tree helpers", () => {
  const routing: TreeFolder = {
    name: "routing",
    path: "rails/routing",
    folders: [],
    pages: [makePage("rails/routing/scope-vs-namespace")],
  };
  const rails: TreeFolder = {
    name: "rails",
    path: "rails",
    folders: [routing],
    pages: [makePage("rails/rails-index"), makePage("rails/foreign-keys")],
  };
  const security: TreeFolder = {
    name: "security",
    path: "security",
    folders: [],
    pages: [makePage("security/hsts")],
  };
  const empty: TreeFolder = {
    name: "empty",
    path: "empty",
    folders: [],
    pages: [],
  };
  const root: TreeFolder = {
    name: "wiki",
    path: "",
    folders: [rails, security, empty],
    pages: [makePage("readme")],
  };

  describe("findFolder", () => {
    it("returns the root for the empty path", () => {
      expect(findFolder(root, "")).toBe(root);
    });

    it("finds a direct child folder", () => {
      expect(findFolder(root, "rails")).toBe(rails);
    });

    it("finds a nested folder via a/b path", () => {
      expect(findFolder(root, "rails/routing")).toBe(routing);
    });

    it("returns null for a missing top-level folder", () => {
      expect(findFolder(root, "missing")).toBeNull();
    });

    it("returns null when a nested segment is missing", () => {
      expect(findFolder(root, "rails/missing")).toBeNull();
    });
  });

  describe("countPages", () => {
    it("counts pages recursively across nested folders", () => {
      // readme + rails-index + foreign-keys + scope-vs-namespace + hsts
      expect(countPages(root)).toBe(5);
    });

    it("counts a subtree including its nested folders", () => {
      expect(countPages(rails)).toBe(3);
    });

    it("counts a leaf folder", () => {
      expect(countPages(routing)).toBe(1);
    });

    it("returns 0 for an empty folder", () => {
      expect(countPages(empty)).toBe(0);
    });
  });

  describe("topLevelFolder", () => {
    it("returns the first segment of a nested path", () => {
      expect(topLevelFolder("rails/foreign-keys")).toBe("rails");
      expect(topLevelFolder("rails/routing/scope-vs-namespace")).toBe("rails");
    });

    it("returns 'wiki' for a bare top-level page", () => {
      expect(topLevelFolder("page")).toBe("wiki");
    });

    it("returns 'wiki' for the empty string", () => {
      expect(topLevelFolder("")).toBe("wiki");
    });
  });
});
