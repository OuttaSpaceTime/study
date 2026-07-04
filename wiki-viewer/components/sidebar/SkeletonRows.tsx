"use client";

/** Quiet placeholder rows while the wiki index has not loaded yet. */
export default function SkeletonRows() {
  const widths = ["70%", "50%", "62%", "44%", "56%", "38%"];
  return (
    <div className="space-y-2.5 px-3 py-4" aria-hidden="true">
      {widths.map((width, i) => (
        <div
          key={i}
          className="h-3.5 animate-pulse rounded bg-panel-2"
          style={{ width }}
        />
      ))}
    </div>
  );
}
