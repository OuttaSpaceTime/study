import Link from "next/link";
import type { PageMeta } from "@/lib/types";
import { topicColor } from "@/lib/colors";

/**
 * Graph-shaped prev/next footer: backlinks answer "where did I come from?",
 * outbound links answer "where do I want to go?".
 */
export default function Connections({
  meta,
  byPath,
}: {
  meta: PageMeta;
  byPath: Map<string, PageMeta>;
}) {
  if (meta.inbound.length === 0 && meta.outbound.length === 0) return null;
  return (
    <footer className="mt-16 border-t border-border pt-8">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <ConnectionColumn
          label="← Linked from"
          paths={meta.inbound}
          byPath={byPath}
          emptyText="nothing links here yet"
        />
        <ConnectionColumn
          label="Links to →"
          paths={meta.outbound}
          byPath={byPath}
          emptyText="no outgoing links"
        />
      </div>
    </footer>
  );
}

function ConnectionColumn({
  label,
  paths,
  byPath,
  emptyText,
}: {
  label: string;
  paths: string[];
  byPath: Map<string, PageMeta>;
  emptyText: string;
}) {
  return (
    <div className="min-w-0">
      <h2 className="text-[11px] font-medium uppercase tracking-wider text-faint">
        {label}
      </h2>
      <div className="mt-3 flex flex-col gap-2">
        {paths.length === 0 ? (
          <p className="px-1 py-2 text-[13px] text-faint">{emptyText}</p>
        ) : (
          paths.map((path) => {
            const target = byPath.get(path);
            const folder = target?.folder ?? path.split("/").slice(0, -1).join("/");
            const topic = folder.split("/")[0] || "wiki";
            return (
              <Link
                key={path}
                href={`/wiki/${path}`}
                className="group rounded-lg border border-border bg-panel px-4 py-3 shadow-xs shadow-black/5 transition-[color,border-color,box-shadow] hover:border-accent/40 hover:shadow-sm"
              >
                <span className="block truncate text-[14px] font-medium text-fg transition-colors group-hover:text-accent">
                  {target?.title ?? path}
                </span>
                <span className="mt-1 flex items-center gap-1.5 text-xs text-faint">
                  <span
                    aria-hidden
                    className="inline-block size-1.5 rounded-full"
                    style={{ backgroundColor: topicColor(folder) }}
                  />
                  {topic}
                </span>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
}
