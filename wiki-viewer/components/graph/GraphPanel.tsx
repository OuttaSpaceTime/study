"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import clsx from "clsx";
import {
  useCurrentPagePath,
  useWikiData,
} from "@/components/providers/WikiDataProvider";
import type { GraphLink, GraphNode } from "@/lib/types";

const MODE_KEY = "wiki-viewer.graph-mode";

type GraphMode = "local" | "all";

interface GraphShape {
  nodes: GraphNode[];
  links: GraphLink[];
}

function GraphPlaceholder() {
  return (
    <div className="flex h-full items-center justify-center text-xs text-faint">
      graph
    </div>
  );
}

// react-force-graph-2d touches window/canvas at import time, so the canvas
// component is only ever loaded in the browser.
const GraphCanvas = dynamic(() => import("./GraphCanvas"), {
  ssr: false,
  loading: () => <GraphPlaceholder />,
});

/** Subgraph of `focus` plus neighbors within 2 hops (undirected). */
function localSubgraph(graph: GraphShape, focus: string): GraphShape {
  if (!graph.nodes.some((node) => node.id === focus)) return graph;

  const adjacency = new Map<string, string[]>();
  const add = (from: string, to: string) => {
    const list = adjacency.get(from);
    if (list) list.push(to);
    else adjacency.set(from, [to]);
  };
  for (const link of graph.links) {
    add(link.source, link.target);
    add(link.target, link.source);
  }

  const keep = new Set([focus]);
  let frontier = [focus];
  for (let hop = 0; hop < 2; hop += 1) {
    const next: string[] = [];
    for (const id of frontier) {
      for (const neighbor of adjacency.get(id) ?? []) {
        if (!keep.has(neighbor)) {
          keep.add(neighbor);
          next.push(neighbor);
        }
      }
    }
    frontier = next;
  }

  return {
    nodes: graph.nodes.filter((node) => keep.has(node.id)),
    links: graph.links.filter(
      (link) => keep.has(link.source) && keep.has(link.target),
    ),
  };
}

interface GraphPanelProps {
  /** "rail" shows collapse/fullscreen buttons; "fullscreen" shows a close button. */
  variant?: "rail" | "fullscreen";
  onCollapse?: () => void;
  onEnterFullscreen?: () => void;
  onExitFullscreen?: () => void;
}

export default function GraphPanel({
  variant = "rail",
  onCollapse,
  onEnterFullscreen,
  onExitFullscreen,
}: GraphPanelProps) {
  const { data, byPath } = useWikiData();
  const currentPath = useCurrentPagePath();
  const [mode, setMode] = useState<GraphMode>("local");

  // localStorage is read after mount so the SSR-rendered markup stays stable.
  useEffect(() => {
    const stored = window.localStorage.getItem(MODE_KEY);
    if (stored === "local" || stored === "all") {
      // One-time client-only init; the server cannot know the stored mode.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMode(stored);
    }
  }, []);

  const selectMode = (next: GraphMode) => {
    setMode(next);
    window.localStorage.setItem(MODE_KEY, next);
  };

  // Keyed on the *effective* focus: in All mode the focus stays null across
  // navigation, so the memoized object is stable and the simulation does not
  // restart on every page change.
  const focus = mode === "local" ? currentPath : null;
  const graphData = useMemo(() => {
    if (!data) return null;
    const scoped = focus ? localSubgraph(data.graph, focus) : data.graph;
    // force-graph mutates node/link objects (positions, resolved endpoint
    // refs) — never hand it the provider's originals.
    return {
      nodes: scoped.nodes.map((node) => ({ ...node })),
      links: scoped.links.map((link) => ({ ...link })),
    };
  }, [data, focus]);

  const currentTitle = currentPath
    ? (byPath.get(currentPath)?.title ?? currentPath)
    : null;

  return (
    <section className="flex h-full flex-col">
      <header className="flex shrink-0 items-center gap-3 border-b border-border px-3 py-1.5">
        <span className="shrink-0 text-[11px] font-medium uppercase tracking-wider text-faint">
          Graph
        </span>
        {variant === "fullscreen" && currentTitle && (
          <span className="min-w-0 truncate text-[12px] text-muted">
            → {currentTitle}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <div className="flex rounded-md bg-panel-2 p-0.5">
            {(["local", "all"] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => selectMode(option)}
                className={clsx(
                  "rounded px-2 py-0.5 text-[11px] capitalize transition-colors",
                  mode === option
                    ? "bg-accent-soft text-accent"
                    : "text-muted hover:text-fg",
                )}
              >
                {option}
              </button>
            ))}
          </div>
          {graphData && (
            <span className="text-[11px] tabular-nums text-faint">
              {graphData.nodes.length} nodes
            </span>
          )}
          {variant === "rail" ? (
            <>
              <HeaderButton title="Fullscreen graph" onClick={onEnterFullscreen}>
                <FullscreenIcon />
              </HeaderButton>
              <HeaderButton title="Collapse graph" onClick={onCollapse}>
                <CollapsePanelIcon />
              </HeaderButton>
            </>
          ) : (
            <HeaderButton title="Exit fullscreen (Esc)" onClick={onExitFullscreen}>
              <CloseIcon />
            </HeaderButton>
          )}
        </div>
      </header>
      <div className="min-h-0 flex-1">
        {graphData ? (
          <GraphCanvas graphData={graphData} currentPath={currentPath} />
        ) : (
          <GraphPlaceholder />
        )}
      </div>
    </section>
  );
}

function HeaderButton({
  title,
  onClick,
  children,
}: {
  title: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      aria-label={title}
      onClick={onClick}
      className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-muted transition-colors hover:bg-panel-2 hover:text-fg"
    >
      {children}
    </button>
  );
}

function FullscreenIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 2H2v4M10 2h4v4M6 14H2v-4M10 14h4v-4" />
    </svg>
  );
}

function CollapsePanelIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 3l5 5-5 5" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <path d="M3 3l10 10M13 3L3 13" />
    </svg>
  );
}
