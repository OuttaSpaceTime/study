"use client";

// Smart left sidebar with three persisted states:
//   rail    — collapsed icon strip (52px)
//   context — DEFAULT: where am I / what is around me / how do I go up (280px)
//   tree    — full collapsible wiki tree (300px)

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { useCurrentPagePath } from "@/components/providers/WikiDataProvider";
import { ResizeHandle, usePanelResize } from "@/components/panel-resize";
import ContextPanel from "./ContextPanel";
import TreePanel from "./TreePanel";
import {
  CollapseIcon,
  ExpandIcon,
  GlyphIcon,
  SearchIcon,
  TreeIcon,
} from "./icons";

type SidebarMode = "rail" | "context" | "tree";

const STORAGE_KEY = "wiki-viewer.sidebar";
const RAIL_WIDTH = 52;

function openPalette() {
  window.dispatchEvent(new CustomEvent("wiki:open-palette"));
}

function IconButton({
  title,
  onClick,
  active = false,
  children,
}: {
  title: string;
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className={clsx(
        "flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors",
        active
          ? "bg-accent-soft text-accent"
          : "text-muted hover:bg-panel-2 hover:text-fg",
      )}
    >
      {children}
    </button>
  );
}

export default function Sidebar() {
  // Default to "context" on the server and first client paint; the stored
  // mode is applied in an effect to avoid a hydration mismatch.
  const [mode, setMode] = useState<SidebarMode>("context");
  const lastExpanded = useRef<Exclude<SidebarMode, "rail">>("context");
  // Folder paths open in the tree; lives here so it survives mode switches.
  const [openFolders, setOpenFolders] = useState<Set<string>>(new Set());
  const currentPath = useCurrentPagePath();
  const { width, dragging, handleProps } = usePanelResize({
    storageKey: "wiki-viewer.sidebar-width",
    defaultWidth: 280,
    min: 208,
    max: 480,
    edge: "left",
  });

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "rail" || stored === "context" || stored === "tree") {
      // One-time client-only init: the server cannot know the stored mode,
      // so it must be applied after hydration rather than in initial state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode(stored);
      if (stored !== "rail") lastExpanded.current = stored;
    }
  }, []);

  const switchMode = useCallback((next: SidebarMode) => {
    setMode(next);
    if (next !== "rail") lastExpanded.current = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable — state still works for this session.
    }
  }, []);

  // Auto-expand all tree ancestors of the page being viewed. Render-phase
  // state adjustment (guarded by the previous path) per the React docs'
  // "adjusting state when props change" pattern — no effect needed.
  const [autoExpandedFor, setAutoExpandedFor] = useState<string | null>(null);
  if (currentPath !== autoExpandedFor) {
    setAutoExpandedFor(currentPath);
    const segments = currentPath ? currentPath.split("/").slice(0, -1) : [];
    if (segments.length > 0) {
      const next = new Set(openFolders);
      let acc = "";
      for (const segment of segments) {
        acc = acc ? `${acc}/${segment}` : segment;
        next.add(acc);
      }
      if (next.size !== openFolders.size) setOpenFolders(next);
    }
  }

  const toggleFolder = useCallback((path: string) => {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  return (
    <aside
      style={{ width: mode === "rail" ? RAIL_WIDTH : width }}
      className={clsx(
        "relative flex h-full shrink-0 flex-col border-r border-border bg-panel",
        !dragging && "transition-[width] duration-200 ease-out",
      )}
    >
      {mode === "rail" ? (
        <div className="flex flex-col items-center gap-1.5 py-3">
          <Link
            href="/"
            title="Study Wiki"
            className="flex h-7 w-7 items-center justify-center rounded-md text-accent transition-colors hover:bg-panel-2"
          >
            <GlyphIcon />
          </Link>
          <IconButton title="Search ⌘K" onClick={openPalette}>
            <SearchIcon />
          </IconButton>
          <IconButton
            title="Expand sidebar"
            onClick={() => switchMode(lastExpanded.current)}
          >
            <ExpandIcon />
          </IconButton>
        </div>
      ) : (
        <>
          <div className="flex h-12 shrink-0 items-center gap-0.5 border-b border-border px-2">
            <Link
              href="/"
              className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-1 py-1 transition-colors hover:bg-panel-2"
            >
              <span className="shrink-0 text-accent">
                <GlyphIcon />
              </span>
              <span className="truncate text-sm font-medium text-fg">
                Study Wiki
              </span>
            </Link>
            <IconButton title="Search ⌘K" onClick={openPalette}>
              <SearchIcon />
            </IconButton>
            <IconButton
              title={mode === "tree" ? "Context view" : "Tree view"}
              active={mode === "tree"}
              onClick={() => switchMode(mode === "tree" ? "context" : "tree")}
            >
              <TreeIcon />
            </IconButton>
            <IconButton title="Collapse sidebar" onClick={() => switchMode("rail")}>
              <CollapseIcon />
            </IconButton>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto pb-3">
            {mode === "tree" ? (
              <TreePanel openSet={openFolders} onToggle={toggleFolder} />
            ) : (
              <ContextPanel />
            )}
          </div>
        </>
      )}
      {mode !== "rail" && (
        <ResizeHandle side="right" dragging={dragging} handleProps={handleProps} />
      )}
    </aside>
  );
}
