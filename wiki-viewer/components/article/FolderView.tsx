import Link from "next/link";
import clsx from "clsx";
import type { TreeFolder } from "@/lib/types";
import { topicColor } from "@/lib/colors";
import Breadcrumb from "./Breadcrumb";
import TagChip from "./TagChip";

function countPages(folder: TreeFolder): number {
  return (
    folder.pages.length +
    folder.folders.reduce((sum, child) => sum + countPages(child), 0)
  );
}

export default function FolderView({ folder }: { folder: TreeFolder }) {
  const parentPath = folder.path.split("/").slice(0, -1).join("/");
  const accent = topicColor(folder.path);
  // Tree pages are already sorted index-first (MOC pinned), then by title.
  return (
    <div className="mx-auto w-full max-w-3xl px-8 py-10">
      <header className="mb-8">
        <Breadcrumb folder={parentPath} />
        <h1 className="mt-3 flex items-center gap-2.5 text-3xl font-semibold tracking-tight text-fg">
          <span
            aria-hidden
            className="inline-block size-2.5 rounded-full"
            style={{ backgroundColor: accent }}
          />
          {folder.name}
        </h1>
        <p className="mt-2 text-[12px] text-faint">
          {countPages(folder)} page{countPages(folder) === 1 ? "" : "s"}
        </p>
      </header>

      {folder.folders.length > 0 && (
        <section className="mb-8">
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-faint">
            Folders
          </h2>
          <ul className="mt-2 overflow-hidden rounded-lg border border-border">
            {folder.folders.map((child) => (
              <li key={child.path} className="border-b border-border last:border-b-0">
                <Link
                  href={`/wiki/${child.path}`}
                  className="flex items-baseline justify-between gap-3 px-3 py-2 text-muted transition-colors hover:bg-panel-2 hover:text-fg"
                >
                  <span className="text-[14px] font-medium">{child.name}/</span>
                  <span className="text-[12px] text-faint">
                    {countPages(child)} page{countPages(child) === 1 ? "" : "s"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {folder.pages.length > 0 && (
        <section>
          <h2 className="text-[11px] font-medium uppercase tracking-wider text-faint">
            Pages
          </h2>
          <ul className="mt-2 overflow-hidden rounded-lg border border-border">
            {folder.pages.map((page) => (
              <li key={page.path} className="border-b border-border last:border-b-0">
                <Link
                  href={`/wiki/${page.path}`}
                  className={clsx(
                    "flex flex-wrap items-baseline gap-x-3 gap-y-1 px-3 py-2 transition-colors hover:bg-panel-2",
                    page.isIndex
                      ? "bg-accent-soft text-accent hover:text-accent"
                      : "text-muted hover:text-fg",
                  )}
                >
                  <span className="text-[14px] font-medium">{page.title}</span>
                  {page.isIndex && (
                    <span className="text-[11px] uppercase tracking-wider">
                      moc
                    </span>
                  )}
                  <span className="flex flex-1 flex-wrap items-baseline justify-end gap-x-3 gap-y-1">
                    <span className="flex flex-wrap gap-1.5">
                      {page.tags.map((tag) => (
                        <TagChip key={tag} tag={tag} />
                      ))}
                    </span>
                    {page.updated && (
                      <span className="text-[12px] text-faint">
                        {page.updated}
                      </span>
                    )}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
