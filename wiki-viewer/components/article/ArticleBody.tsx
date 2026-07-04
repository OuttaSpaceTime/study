// Server component: react-markdown is synchronous, so the whole article can
// render on the server and pick up wiki file edits on every reload.
import { isValidElement, type ReactNode } from "react";
import Link from "next/link";
import Markdown, { type Components, type ExtraProps } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import type { PageMeta } from "@/lib/types";
import {
  createWikilinkResolver,
  type MocRef,
  remarkWikilinks,
  slugifyHeading,
  stripLeadingH1,
} from "@/lib/markdown";

/** Flatten React children to plain text for heading slugs. */
function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return textOf(node.props.children);
  }
  return "";
}

/** Strip react-markdown's `node` prop before spreading onto a DOM element. */
function domProps<T extends ExtraProps>(props: T): Omit<T, "node"> {
  const { node, ...rest } = props;
  void node;
  return rest;
}

const components: Components = {
  a(props) {
    const { href = "", children, ...rest } = domProps(props);
    // Internal app routes (/wiki/...) render as next/link so the client
    // panels (sidebar/graph/notes) persist across navigation.
    if (href.startsWith("/")) {
      return (
        <Link href={href} {...rest}>
          {children}
        </Link>
      );
    }
    // Same-page anchors stay plain.
    if (href.startsWith("#")) {
      return (
        <a href={href} {...rest}>
          {children}
        </a>
      );
    }
    // External links open in a new tab.
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
        {children}
      </a>
    );
  },
  h2(props) {
    const { children, ...rest } = domProps(props);
    return (
      <h2 id={slugifyHeading(textOf(children))} {...rest}>
        {children}
      </h2>
    );
  },
  h3(props) {
    const { children, ...rest } = domProps(props);
    return (
      <h3 id={slugifyHeading(textOf(children))} {...rest}>
        {children}
      </h3>
    );
  },
  table(props) {
    const { children, ...rest } = domProps(props);
    return (
      <div className="overflow-x-auto">
        <table {...rest}>{children}</table>
      </div>
    );
  },
};

export default function ArticleBody({
  markdown,
  pages,
  mocs = [],
}: {
  markdown: string;
  pages: PageMeta[];
  mocs?: MocRef[];
}) {
  const resolve = createWikilinkResolver(pages, mocs);
  return (
    <article className="wiki-prose prose max-w-none">
      <Markdown
        remarkPlugins={[remarkGfm, [remarkWikilinks, { resolve }]]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {stripLeadingH1(markdown)}
      </Markdown>
    </article>
  );
}
