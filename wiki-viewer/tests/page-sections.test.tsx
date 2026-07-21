// Tests for the sidebar mini-TOC (components/sidebar/PageSections.tsx).
// Rendered with renderToStaticMarkup so effects (scroll-spy, localStorage)
// don't run — this asserts the default, expanded server/first-paint output.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import PageSections from "@/components/sidebar/PageSections";

const SECTIONS = ["TL;DR", "The signature is a contract", "Why review is the backstop"];

function render(sections: string[]): string {
  return renderToStaticMarkup(
    <PageSections path="software-design/reading-code-for-intent" sections={sections} paddingLeft={26} />,
  );
}

describe("PageSections", () => {
  it("renders the 'On this page' toggle expanded by default", () => {
    const html = render(SECTIONS);
    expect(html).toContain("On this page");
    expect(html).toContain('aria-expanded="true"');
  });

  it("renders one jump-link per section with a slugified anchor", () => {
    const html = render(SECTIONS);
    expect(html).toContain(
      'href="/wiki/software-design/reading-code-for-intent#tldr"',
    );
    expect(html).toContain(
      'href="/wiki/software-design/reading-code-for-intent#the-signature-is-a-contract"',
    );
    expect(html).toContain(
      'href="/wiki/software-design/reading-code-for-intent#why-review-is-the-backstop"',
    );
  });

  it("renders the section titles verbatim", () => {
    const html = render(SECTIONS);
    for (const section of SECTIONS) expect(html).toContain(section);
  });

  it("renders nothing when the page has no H2 sections", () => {
    expect(render([])).toBe("");
  });
});
