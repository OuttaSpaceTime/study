"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { usePathname } from "next/navigation";
import type { PageMeta, WikiIndexPayload } from "@/lib/types";

interface WikiDataContextValue {
  /** Null until the first /api/index fetch resolves. */
  data: WikiIndexPayload | null;
  byPath: Map<string, PageMeta>;
  refresh: () => Promise<void>;
}

const WikiDataContext = createContext<WikiDataContextValue>({
  data: null,
  byPath: new Map(),
  refresh: async () => {},
});

export function WikiDataProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<WikiIndexPayload | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/index");
      if (res.ok) setData(await res.json());
    } catch {
      // Offline dev server hiccup — keep last known data.
    }
  }, []);

  useEffect(() => {
    // Initial client-side data fetch (setData fires after the await, not
    // synchronously in the effect body).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [refresh]);

  const byPath = useMemo(
    () => new Map((data?.pages ?? []).map((p) => [p.path, p])),
    [data],
  );

  const value = useMemo(() => ({ data, byPath, refresh }), [data, byPath, refresh]);
  return (
    <WikiDataContext.Provider value={value}>{children}</WikiDataContext.Provider>
  );
}

export function useWikiData(): WikiDataContextValue {
  return useContext(WikiDataContext);
}

/** Wiki path of the page currently shown, e.g. "rails/foreign-keys", or null off /wiki/ routes. */
export function useCurrentPagePath(): string | null {
  const pathname = usePathname();
  if (!pathname.startsWith("/wiki/")) return null;
  const rest = pathname
    .slice("/wiki/".length)
    .split("/")
    .map(decodeURIComponent)
    .join("/");
  return rest || null;
}
