"use client";

// Global Ctrl+K / Cmd+K page switcher. Also opens on the `wiki:open-palette`
// CustomEvent dispatched by the sidebar.
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useWikiData } from "@/components/providers/WikiDataProvider";
import { topicColor } from "@/lib/colors";
import type { PageMeta } from "@/lib/types";

interface Result {
  page: PageMeta;
  /** Set when an alias (not the title) is what matched the query. */
  matchedAlias?: string;
}

function scorePage(
  page: PageMeta,
  query: string,
): { score: number; matchedAlias?: string } | null {
  const title = page.title.toLowerCase();
  if (title.startsWith(query)) return { score: 5 };
  if (title.includes(query)) return { score: 4 };
  const alias = page.aliases.find((a) => a.toLowerCase().includes(query));
  if (alias) return { score: 3, matchedAlias: alias };
  if (page.path.toLowerCase().includes(query)) return { score: 2 };
  if (page.tags.some((t) => t.toLowerCase().includes(query))) {
    return { score: 1 };
  }
  return null;
}

const MAX_RESULTS = 10;

export default function CommandPalette() {
  const { data } = useWikiData();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const selectedRef = useRef<HTMLButtonElement | null>(null);

  // Open/close triggers.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
        setQuery("");
        setSelected(0);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    const onOpenEvent = () => {
      setOpen(true);
      setQuery("");
      setSelected(0);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("wiki:open-palette", onOpenEvent);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("wiki:open-palette", onOpenEvent);
    };
  }, []);

  // Body scroll lock while open.
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  const results = useMemo<Result[]>(() => {
    const pages = data?.pages ?? [];
    const q = query.trim().toLowerCase();
    if (!q) {
      return [...pages]
        .sort((a, b) => b.updated.localeCompare(a.updated))
        .slice(0, MAX_RESULTS)
        .map((page) => ({ page }));
    }
    return pages
      .map((page) => ({ page, match: scorePage(page, q) }))
      .filter(
        (r): r is { page: PageMeta; match: NonNullable<typeof r.match> } =>
          r.match !== null,
      )
      .sort(
        (a, b) =>
          b.match.score - a.match.score ||
          a.page.title.localeCompare(b.page.title),
      )
      .slice(0, MAX_RESULTS)
      .map(({ page, match }) => ({ page, matchedAlias: match.matchedAlias }));
  }, [data, query]);

  const selectedIndex =
    results.length > 0 ? Math.min(selected, results.length - 1) : 0;

  // Keep the keyboard-selected row visible.
  useEffect(() => {
    selectedRef.current?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex, results]);

  if (!open) return null;

  const navigateTo = (page: PageMeta) => {
    setOpen(false);
    router.push(`/wiki/${page.path}`);
  };

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelected(Math.min(selectedIndex + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelected(Math.max(selectedIndex - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const hit = results[selectedIndex];
      if (hit) navigateTo(hit.page);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-center bg-black/20 pt-[20vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="h-fit w-full max-w-xl overflow-hidden rounded-lg border border-border bg-panel shadow-xl shadow-black/10"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelected(0);
          }}
          onKeyDown={onInputKeyDown}
          placeholder="Go to page…"
          className="w-full border-b border-border bg-transparent px-4 py-3 text-sm text-fg outline-none placeholder:text-faint"
        />
        <ul className="max-h-80 overflow-y-auto p-1">
          {results.length === 0 ? (
            <li className="px-3 py-2 text-sm text-faint">
              {data === null ? "Loading index…" : "No matches."}
            </li>
          ) : (
            results.map((result, i) => (
              <li key={result.page.path}>
                <button
                  type="button"
                  ref={(el) => {
                    if (i === selectedIndex) selectedRef.current = el;
                  }}
                  onMouseMove={() => setSelected(i)}
                  onClick={() => navigateTo(result.page)}
                  className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors ${
                    i === selectedIndex ? "bg-panel-2 text-fg" : "text-muted"
                  }`}
                >
                  <span className="truncate text-sm">{result.page.title}</span>
                  {result.matchedAlias && (
                    <span className="truncate text-xs text-faint">
                      → {result.matchedAlias}
                    </span>
                  )}
                  <span
                    className="ml-auto shrink-0 text-xs"
                    style={{ color: topicColor(result.page.folder) }}
                  >
                    {result.page.folder.split("/")[0] || "wiki"}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
        <div className="border-t border-border px-3 py-1.5 text-[11px] text-faint">
          ↑↓ navigate · ↵ open · esc close
        </div>
      </div>
    </div>
  );
}
