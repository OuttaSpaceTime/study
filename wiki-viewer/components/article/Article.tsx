import type { ChallengeDetail } from "@/lib/challenge-types";
import type { MocRef } from "@/lib/markdown";
import type { PageMeta, WikiPage } from "@/lib/types";
import ArticleHeader from "./ArticleHeader";
import ArticleBody from "./ArticleBody";
import Connections from "./Connections";

export default function Article({
  page,
  pages,
  mocs = [],
  challenges = [],
}: {
  page: WikiPage;
  pages: PageMeta[];
  mocs?: MocRef[];
  challenges?: ChallengeDetail[];
}) {
  const byPath = new Map(pages.map((p) => [p.path, p]));
  return (
    <div className="mx-auto w-full max-w-3xl px-8 py-12">
      <ArticleHeader meta={page.meta} />
      <ArticleBody
        markdown={page.markdown}
        pages={pages}
        mocs={mocs}
        challenges={challenges}
      />
      <Connections meta={page.meta} byPath={byPath} />
    </div>
  );
}
