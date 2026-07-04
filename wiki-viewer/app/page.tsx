// Dashboard: review queue, recent activity, topic overview.
import Link from "next/link";
import { getWikiIndex } from "@/lib/wiki";
import { topicColor } from "@/lib/colors";
import type { PageMeta, TreeFolder } from "@/lib/types";

export const dynamic = "force-dynamic";

// Rose from lib/colors.ts PALETTE — the theme has no red token and the
// overdue tag needs to read as a warning.
const OVERDUE_COLOR = "#c2405a";

function countPages(folder: TreeFolder): number {
  return (
    folder.pages.length +
    folder.folders.reduce((n, child) => n + countPages(child), 0)
  );
}

function collectPages(folder: TreeFolder): PageMeta[] {
  return [...folder.pages, ...folder.folders.flatMap(collectPages)];
}

function TopicChip({ folder }: { folder: string }) {
  const color = topicColor(folder);
  return (
    <span
      className="shrink-0 rounded-full px-1.5 py-px text-[10px] font-medium"
      style={{ color, backgroundColor: `${color}1f` }}
    >
      {folder.split("/")[0] || "wiki"}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-2 px-2 text-[11px] font-medium uppercase tracking-wider text-faint">
      {children}
    </h2>
  );
}

const ROW_CLASS =
  "flex items-center gap-3 rounded-md px-2 py-1 text-muted transition-colors hover:bg-panel-2 hover:text-fg";

export default async function Home() {
  const index = await getWikiIndex();
  const today = new Date().toISOString().slice(0, 10);

  const due = index.pages
    .filter((p) => p.nextReview !== "" && p.nextReview <= today)
    .sort((a, b) => a.nextReview.localeCompare(b.nextReview));

  const recent = [...index.pages]
    .sort((a, b) => b.updated.localeCompare(a.updated))
    .slice(0, 8);

  const topics = index.tree.folders;

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <header className="mb-10 px-2">
        <h1 className="text-xl font-semibold text-fg">Study Wiki</h1>
        <p className="mt-1 text-sm text-muted">
          {index.pages.length} pages · {topics.length} topics ·{" "}
          {index.graph.links.length} links
        </p>
      </header>

      <section className="mb-10">
        <SectionLabel>Due for review</SectionLabel>
        {due.length === 0 ? (
          <p className="px-2 text-sm text-faint">Nothing due. ✨</p>
        ) : (
          <ul>
            {due.map((page) => {
              const overdueDays = Math.round(
                (Date.parse(today) - Date.parse(page.nextReview)) / 86_400_000,
              );
              return (
                <li key={page.path}>
                  <Link href={`/wiki/${page.path}`} className={ROW_CLASS}>
                    <span className="truncate text-sm text-fg">
                      {page.title}
                    </span>
                    <TopicChip folder={page.folder} />
                    <span className="ml-auto shrink-0 font-mono text-xs text-faint">
                      {page.nextReview}
                    </span>
                    {overdueDays > 0 && (
                      <span
                        className="shrink-0 rounded-full px-1.5 py-px text-[10px] font-medium"
                        style={{
                          color: OVERDUE_COLOR,
                          backgroundColor: `${OVERDUE_COLOR}1f`,
                        }}
                      >
                        {overdueDays}d overdue
                      </span>
                    )}
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="mb-10">
        <SectionLabel>Recently updated</SectionLabel>
        <ul>
          {recent.map((page) => (
            <li key={page.path}>
              <Link href={`/wiki/${page.path}`} className={ROW_CLASS}>
                <span className="truncate text-sm text-fg">{page.title}</span>
                <TopicChip folder={page.folder} />
                <span className="ml-auto shrink-0 font-mono text-xs text-faint">
                  {page.updated}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <SectionLabel>Topics</SectionLabel>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {topics.map((folder) => {
            const recentTitles = collectPages(folder)
              .sort((a, b) => b.updated.localeCompare(a.updated))
              .slice(0, 3);
            return (
              <Link
                key={folder.path}
                href={`/wiki/${folder.path}`}
                className="rounded-lg border border-border bg-panel p-3 transition-colors hover:bg-panel-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ backgroundColor: topicColor(folder.path) }}
                  />
                  <span className="truncate text-sm font-medium text-fg">
                    {folder.name}
                  </span>
                  <span className="ml-auto shrink-0 text-xs text-faint">
                    {countPages(folder)}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {recentTitles.map((page) => (
                    <span
                      key={page.path}
                      className="max-w-full truncate rounded bg-panel-2 px-1.5 py-px text-[10px] text-faint"
                    >
                      {page.title}
                    </span>
                  ))}
                </div>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
