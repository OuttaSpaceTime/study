// Tests for lib/srcdoc.ts — sandboxed iframe document construction.
import { describe, expect, it } from "vitest";
import { buildSrcdoc } from "@/lib/srcdoc";

describe("buildSrcdoc", () => {
  it("composes html, css and js into one document", () => {
    const doc = buildSrcdoc([
      { lang: "html", code: "<p>hi</p>" },
      { lang: "css", code: "p { color: red; }" },
      { lang: "js", code: "console.log('x')" },
    ]);
    expect(doc).toContain("<p>hi</p>");
    expect(doc).toContain("p { color: red; }");
    expect(doc).toContain("console.log('x')");
    expect(doc.indexOf("<style>")).toBeLessThan(doc.indexOf("<p>hi</p>"));
    expect(doc.indexOf("<p>hi</p>")).toBeLessThan(doc.indexOf("console.log('x')"));
  });

  it("captures console output via postMessage", () => {
    const doc = buildSrcdoc([{ lang: "js", code: "console.log(1)" }]);
    expect(doc).toContain("study-console");
    expect(doc).toContain("postMessage");
    expect(doc.indexOf("study-console")).toBeLessThan(doc.indexOf("console.log(1)"));
  });

  it("escapes </script> inside user js so it cannot break out", () => {
    const doc = buildSrcdoc([
      { lang: "js", code: 'const s = "</script><script>alert(1)</script>"' },
    ]);
    expect(doc).not.toContain('"</script><script>alert(1)');
    expect(doc).toContain("<\\/script>");
  });

  it("react preset loads vendored classic scripts and a text/babel block", () => {
    const doc = buildSrcdoc(
      [{ lang: "jsx", code: "root.render(<b>hi</b>)" }],
      "react",
    );
    expect(doc).toContain('src="/vendor/react.production.min.js"');
    expect(doc).toContain('src="/vendor/react-dom.production.min.js"');
    expect(doc).toContain('src="/vendor/babel.min.js"');
    expect(doc).toContain('type="text/babel"');
    expect(doc).toContain('<div id="root">');
    expect(doc).toContain("root.render(<b>hi</b>)");
  });

  it("plain preset does not load vendor scripts", () => {
    const doc = buildSrcdoc([{ lang: "js", code: "1" }]);
    expect(doc).not.toContain("/vendor/");
  });
});
