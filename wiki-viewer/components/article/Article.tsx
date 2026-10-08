import type { PageMeta, WikiPage } from "@/lib/types";
import ArticleHeader from "./ArticleHeader";
import ArticleBody from "./ArticleBody";
import Connections from "./Connections";

export default function Article({
  page,
  pages,
}: {
  page: WikiPage;
  pages: PageMeta[];
}) {
  const byPath = new Map(pages.map((p) => [p.path, p]));
  return (
    <div className="mx-auto w-full max-w-3xl px-8 py-12">
      <ArticleHeader meta={page.meta} />
      <ArticleBody markdown={page.markdown} pages={pages} />
      <Connections meta={page.meta} byPath={byPath} />
    </div>
  );
}
