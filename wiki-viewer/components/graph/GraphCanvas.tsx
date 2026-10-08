"use client";

// Statically imports react-force-graph-2d, which is browser-only — this
// module must only be loaded via next/dynamic({ ssr: false }) (see GraphPanel).
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ForceGraph2D from "react-force-graph-2d";
import type {
  ForceGraphMethods,
  LinkObject,
  NodeObject,
} from "react-force-graph-2d";
import { topicColor } from "@/lib/colors";
import type { GraphLink, GraphNode } from "@/lib/types";

type FGNode = NodeObject<GraphNode>;
type FGLink = LinkObject<GraphNode, GraphLink>;
type FGMethods = ForceGraphMethods<
  NodeObject<GraphNode>,
  LinkObject<GraphNode, GraphLink>
>;

// Canvas painting can't consume Tailwind classes; these literals mirror the
// theme tokens in app/globals.css (--color-fg / --color-muted / --color-accent).
const FG = "#2b2e36";
const MUTED = "#6e7380";
const ACCENT = "#4a5fc1";
const LINK = "rgba(74, 95, 193, 0.16)";
const LINK_CURRENT = "rgba(74, 95, 193, 0.55)";
const LABEL_FONT = "ui-sans-serif, system-ui, sans-serif";

function nodeRadius(node: FGNode): number {
  return 1.8 + 0.8 * Math.sqrt(node.linkCount);
}

/** Subset of the d3 force interfaces we tune (the .d.ts only types ForceFn). */
interface TunableForce {
  strength?: (s: number) => TunableForce;
  distance?: (d: number) => TunableForce;
}

/** Screen-constant label with a panel-colored halo so it stays readable over
 * links and neighboring nodes. */
function paintLabel(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  globalScale: number,
  color: string,
) {
  const fontSize = 11 / globalScale;
  ctx.font = `${fontSize}px ${LABEL_FONT}`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.lineWidth = 3 / globalScale;
  ctx.strokeStyle = "rgba(253, 253, 251, 0.9)";
  ctx.strokeText(text, x, y);
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
}

/** Link endpoints start as path strings; force-graph swaps in node objects. */
function endpointId(end: unknown): string | null {
  if (typeof end === "string") return end;
  if (typeof end === "number") return String(end);
  if (end && typeof end === "object") {
    const id = (end as FGNode).id;
    return id == null ? null : String(id);
  }
  return null;
}

interface GraphCanvasProps {
  graphData: { nodes: GraphNode[]; links: GraphLink[] };
  currentPath: string | null;
}

export default function GraphCanvas({
  graphData,
  currentPath,
}: GraphCanvasProps) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fgRef = useRef<FGMethods | undefined>(undefined);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const [hoverId, setHoverId] = useState<string | null>(null);
  const didFitRef = useRef(false);

  // The canvas gets explicit width/height from the panel body, so it can
  // never overflow it.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) {
        setDims({ width: Math.floor(rect.width), height: Math.floor(rect.height) });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Fit once per dataset (initial cooldown, or a mode/page-driven change) —
  // not after every drag-induced engine reheat.
  useEffect(() => {
    didFitRef.current = false;
  }, [graphData]);

  // Spread the layout beyond the d3 defaults (charge -30, distance 30) so
  // nodes stop piling up and labels get room to breathe.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    (fg.d3Force("charge") as TunableForce | undefined)?.strength?.(-60);
    (fg.d3Force("link") as TunableForce | undefined)?.distance?.(45);
    fg.d3ReheatSimulation();
  }, [graphData]);

  const handleEngineStop = useCallback(() => {
    if (didFitRef.current) return;
    didFitRef.current = true;
    fgRef.current?.zoomToFit(400, 40);
  }, []);

  const paintNode = useCallback(
    (node: FGNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const isCurrent = node.id === currentPath;
      const isHovered = node.id === hoverId;
      const radius = nodeRadius(node) + (isCurrent ? 1 : 0);
      const color = topicColor(node.folder);

      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      if (isCurrent) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 2.2, 0, 2 * Math.PI);
        ctx.strokeStyle = ACCENT;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      if (isCurrent || isHovered || globalScale > 1.2) {
        paintLabel(
          ctx,
          node.title,
          x,
          y + radius + 3 / globalScale,
          globalScale,
          isCurrent || isHovered ? FG : MUTED,
        );
      }
    },
    [currentPath, hoverId],
  );

  const paintPointerArea = useCallback(
    (node: FGNode, color: string, ctx: CanvasRenderingContext2D) => {
      ctx.beginPath();
      ctx.arc(node.x ?? 0, node.y ?? 0, nodeRadius(node) + 2, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();
    },
    [],
  );

  const linkColor = useCallback(
    (link: FGLink) => {
      if (!currentPath) return LINK;
      const touchesCurrent =
        endpointId(link.source) === currentPath ||
        endpointId(link.target) === currentPath;
      return touchesCurrent ? LINK_CURRENT : LINK;
    },
    [currentPath],
  );

  const handleNodeClick = useCallback(
    (node: FGNode) => {
      if (!node.id) return;
      router.push(`/wiki/${node.id}`);
    },
    [router],
  );

  const handleNodeHover = useCallback((node: FGNode | null) => {
    setHoverId(node?.id ? String(node.id) : null);
    if (containerRef.current) {
      containerRef.current.style.cursor = node ? "pointer" : "default";
    }
  }, []);

  return (
    <div ref={containerRef} className="h-full w-full overflow-hidden">
      {dims.width > 0 && dims.height > 0 && (
        <ForceGraph2D<GraphNode, GraphLink>
          ref={fgRef}
          graphData={graphData}
          width={dims.width}
          height={dims.height}
          backgroundColor="transparent"
          autoPauseRedraw={false}
          warmupTicks={60}
          cooldownTicks={120}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={paintPointerArea}
          linkColor={linkColor}
          linkWidth={1}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onEngineStop={handleEngineStop}
        />
      )}
    </div>
  );
}
