// Dashboard: flashcard entry point, recent activity, topic overview.
import Link from "next/link";
import { getWikiIndex } from "@/lib/wiki";
import { topicColor } from "@/lib/colors";
import { getDeckOverview, getRecentlyStudied } from "@/lib/flashcards";
import { STATE_COLORS } from "@/components/flashcards/lib";
import { recentlyStudiedPages } from "@/app/lib";
import type { PageMeta, TreeFolder } from "@/lib/types";

export const dynamic = "force-dynamic";

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
  // Start the wiki read before the synchronous deck queries so the fs work and
  // the sqlite work overlap on a cold index.
  const indexPromise = getWikiIndex();
  const overview = getDeckOverview();
  const recentCards = getRecentlyStudied();

  const index = await indexPromise;
  const studied = recentlyStudiedPages(index.pages, recentCards);

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
        <SectionLabel>Last studied</SectionLabel>
        {studied.length === 0 ? (
          <p className="px-2 text-sm text-faint">
            No recent reviews touch a wiki page yet.
          </p>
        ) : (
          <ul>
            {studied.map(({ page, cards, lastStudied }) => (
              <li key={page.path}>
                <Link href={`/wiki/${page.path}`} className={ROW_CLASS}>
                  <span className="truncate text-sm text-fg">{page.title}</span>
                  <TopicChip folder={page.folder} />
                  <span className="ml-auto shrink-0 rounded-full bg-accent-soft px-1.5 py-px text-[10px] font-medium text-accent">
                    {cards} card{cards === 1 ? "" : "s"}
                  </span>
                  <span className="shrink-0 font-mono text-xs text-faint">
                    {lastStudied}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {overview && (
        <section className="mb-10">
          <SectionLabel>Flashcards</SectionLabel>
          <Link
            href="/flashcards"
            className="flex items-center gap-4 rounded-lg border border-border bg-panel p-4 transition-colors hover:bg-panel-2"
          >
            <div className="min-w-0">
              <div className="text-sm font-medium text-fg">
                {overview.total} cards across {overview.deckCount}{" "}
                {overview.deckCount === 1 ? "deck" : "decks"}
              </div>
              <div className="mt-0.5 text-xs text-faint">
                Browse, filter by topic, and flip through the deck
              </div>
            </div>
            <div className="ml-auto flex shrink-0 items-center gap-3">
              {overview.states.map((state) => (
                <div key={state.label} className="text-center">
                  <div
                    className="text-sm font-semibold tabular-nums"
                    style={{ color: STATE_COLORS[state.label] }}
                  >
                    {state.count}
                  </div>
                  <div className="text-[10px] uppercase tracking-wide text-faint">
                    {state.label}
                  </div>
                </div>
              ))}
            </div>
          </Link>
        </section>
      )}

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
