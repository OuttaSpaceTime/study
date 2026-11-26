// The wiki parsing rules both readers implement, pinned by one fixture.
//
// ../tests/fixtures/wiki-rules.json is also run by tests/test_wiki_rules_fixture.py
// against the Python side (scripts/wiki). Each reader keeps its own
// implementation; the fixture is what makes them agree.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { slugifyHeading } from "@/lib/markdown";
import { extractLinkTargets, extractSections } from "@/lib/wiki";

interface MarkdownCase {
  name: string;
  markdown: string;
  expected: string[];
  current?: string[];
}
interface InputCase {
  name: string;
  input: string;
  expected: string;
}
interface Fixture {
  link_targets: MarkdownCase[];
  link_targets_known_gaps: { cases: MarkdownCase[] };
  h2: MarkdownCase[];
  heading_slug: { cases: InputCase[] };
}

const fixture: Fixture = JSON.parse(
  fs.readFileSync(
    path.resolve(import.meta.dirname, "../../tests/fixtures/wiki-rules.json"),
    "utf8",
  ),
);

describe("wiki rules fixture", () => {
  it.each(fixture.link_targets)("link targets: $name", (c) => {
    expect(extractLinkTargets(c.markdown)).toEqual(c.expected);
  });

  it.each(fixture.link_targets_known_gaps.cases)(
    "link targets, known gap stays as documented: $name",
    (c) => {
      expect(extractLinkTargets(c.markdown)).toEqual(c.current);
    },
  );

  it.each(fixture.h2)("h2 sections: $name", (c) => {
    expect(extractSections(c.markdown)).toEqual(c.expected);
  });

  it.each(fixture.heading_slug.cases)("heading slug: $name", (c) => {
    expect(slugifyHeading(c.input)).toBe(c.expected);
  });
});
