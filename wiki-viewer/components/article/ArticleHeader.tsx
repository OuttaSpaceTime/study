import type { PageMeta } from "@/lib/types";
import Breadcrumb from "./Breadcrumb";
import TagChip from "./TagChip";
import FlashcardLauncher from "./FlashcardLauncher";

export default function ArticleHeader({ meta }: { meta: PageMeta }) {
  return (
    <header className="mb-8">
      <Breadcrumb folder={meta.folder} />
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-fg">
        {meta.title}
      </h1>
      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-[12px] text-faint">
        {meta.tags.length > 0 && (
          <span className="flex flex-wrap items-center gap-1.5">
            {meta.tags.map((tag) => (
              <TagChip key={tag} tag={tag} />
            ))}
          </span>
        )}
        {meta.created && <span>created {meta.created}</span>}
        {meta.updated && <span>updated {meta.updated}</span>}
        <FlashcardLauncher
          cardIds={meta.flashcardIds}
          pageTitle={meta.title}
          tags={meta.tags}
        />
      </div>
    </header>
  );
}
