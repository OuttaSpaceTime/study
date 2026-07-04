"use client";

// Shared drag-to-resize primitive for the side rails. Pointer capture keeps
// the drag alive over the graph canvas/iframe content; width persists to
// localStorage so it survives reloads (cross-navigation persistence is free —
// the rails live in the root layout and never remount).

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

interface PanelResizeOptions {
  storageKey: string;
  defaultWidth: number;
  min: number;
  max: number;
  /** Screen edge the panel hugs — determines which drag direction grows it. */
  edge: "left" | "right";
}

export interface ResizeHandleProps {
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerMove: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerUp: (e: React.PointerEvent<HTMLDivElement>) => void;
  onPointerCancel: (e: React.PointerEvent<HTMLDivElement>) => void;
}

export function usePanelResize({
  storageKey,
  defaultWidth,
  min,
  max,
  edge,
}: PanelResizeOptions) {
  const [width, setWidth] = useState(defaultWidth);
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{
    startX: number;
    startWidth: number;
    lastWidth: number;
  } | null>(null);

  const clamp = (w: number) => Math.min(max, Math.max(min, w));

  useEffect(() => {
    const stored = Number(window.localStorage.getItem(storageKey));
    if (Number.isFinite(stored) && stored > 0) {
      // One-time client-only init; the server cannot know the stored width.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setWidth(Math.min(max, Math.max(min, stored)));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storageKey]);

  const endDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const finalWidth = drag.current.lastWidth;
    drag.current = null;
    setDragging(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    try {
      window.localStorage.setItem(storageKey, String(finalWidth));
    } catch {
      // Storage unavailable — the size still holds for this session.
    }
  };

  const handleProps: ResizeHandleProps = {
    onPointerDown: (e) => {
      e.preventDefault();
      e.currentTarget.setPointerCapture(e.pointerId);
      // `width` is fresh here: the handlers are recreated every render.
      drag.current = { startX: e.clientX, startWidth: width, lastWidth: width };
      setDragging(true);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    onPointerMove: (e) => {
      if (!drag.current) return;
      const delta = e.clientX - drag.current.startX;
      const next = clamp(
        drag.current.startWidth + (edge === "left" ? delta : -delta),
      );
      drag.current.lastWidth = next;
      setWidth(next);
    },
    onPointerUp: endDrag,
    onPointerCancel: endDrag,
  };

  return { width, dragging, handleProps };
}

/** The draggable divider line. Render inside a `relative` panel. */
export function ResizeHandle({
  side,
  dragging,
  handleProps,
}: {
  /** Which side of the panel the handle sits on. */
  side: "left" | "right";
  dragging: boolean;
  handleProps: ResizeHandleProps;
}) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      className={clsx(
        "absolute inset-y-0 z-20 w-[5px] cursor-col-resize touch-none transition-colors",
        side === "right" ? "-right-[2px]" : "-left-[2px]",
        dragging ? "bg-accent/50" : "hover:bg-accent/30",
      )}
      {...handleProps}
    />
  );
}
