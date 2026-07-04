"use client";

// Right rail housing the graph: drag-resizable, collapsible to a thin strip,
// and expandable to a fullscreen overlay. In fullscreen, clicking a node
// navigates the page *behind* the overlay (the scrim keeps it visible), so
// you can hop through the wiki without leaving the graph.

import { useEffect, useState } from "react";
import clsx from "clsx";
import GraphPanel from "./GraphPanel";
import { ResizeHandle, usePanelResize } from "@/components/panel-resize";

const COLLAPSE_KEY = "wiki-viewer.graph-collapsed";

export default function GraphRail() {
  const [collapsed, setCollapsed] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const { width, dragging, handleProps } = usePanelResize({
    storageKey: "wiki-viewer.graph-width",
    defaultWidth: 380,
    min: 280,
    max: 720,
    edge: "right",
  });

  useEffect(() => {
    if (window.localStorage.getItem(COLLAPSE_KEY) === "1") {
      // One-time client-only init; the server cannot know the stored state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCollapsed(true);
    }
  }, []);

  const toggleCollapsed = (next: boolean) => {
    setCollapsed(next);
    try {
      window.localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
    } catch {
      // Storage unavailable — state still works for this session.
    }
  };

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setFullscreen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [fullscreen]);

  return (
    <>
      <aside
        style={{ width: collapsed ? 40 : width }}
        className={clsx(
          "relative shrink-0 border-l border-border bg-panel",
          !dragging && "transition-[width] duration-200 ease-out",
        )}
      >
        {collapsed ? (
          <button
            type="button"
            title="Show graph"
            onClick={() => toggleCollapsed(false)}
            className="flex h-full w-full flex-col items-center gap-2 pt-3 text-muted transition-colors hover:bg-panel-2 hover:text-fg"
          >
            <GraphGlyph />
            <span className="text-[10px] font-medium uppercase tracking-wider [writing-mode:vertical-rl]">
              Graph
            </span>
          </button>
        ) : (
          <>
            <GraphPanel
              variant="rail"
              onCollapse={() => toggleCollapsed(true)}
              onEnterFullscreen={() => setFullscreen(true)}
            />
            <ResizeHandle side="left" dragging={dragging} handleProps={handleProps} />
          </>
        )}
      </aside>
      {fullscreen && (
        <div className="fixed inset-0 z-40">
          <div
            className="absolute inset-0 bg-black/20"
            onClick={() => setFullscreen(false)}
            aria-hidden
          />
          <div className="absolute inset-6 overflow-hidden rounded-xl border border-border bg-panel shadow-2xl">
            <GraphPanel
              variant="fullscreen"
              onExitFullscreen={() => setFullscreen(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}

function GraphGlyph() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
      <circle cx="4" cy="4" r="2" />
      <circle cx="12" cy="6" r="2" />
      <circle cx="7" cy="12" r="2" />
      <path d="M5.8 4.9 10.2 5.6M5 5.9l1.3 4.3M10.6 7.6 8.3 10.7" />
    </svg>
  );
}
