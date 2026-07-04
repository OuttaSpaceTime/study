"use client";

// TREE state: full collapsible wiki tree. Open/closed state lives in the
// parent Sidebar (a Set of folder paths) so it survives mode switches;
// ancestors of the current page are auto-expanded there too.

import { useEffect, useRef } from "react";
import Link from "next/link";
import clsx from "clsx";
import {
  useCurrentPagePath,
  useWikiData,
} from "@/components/providers/WikiDataProvider";
import type { PageMeta, TreeFolder } from "@/lib/types";
import { ChevronRightIcon } from "./icons";
import { countPages } from "./lib";
import SkeletonRows from "./SkeletonRows";

const INDENT = 12;

function PageRow({
  meta,
  depth,
  current,
}: {
  meta: PageMeta;
  depth: number;
  current: boolean;
}) {
  const ref = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    if (current) ref.current?.scrollIntoView({ block: "nearest" });
  }, [current]);

  return (
    <Link
      ref={ref}
      href={`/wiki/${meta.path}`}
      className={clsx(
        "flex items-center gap-1.5 rounded-md px-2 py-[3px] text-[13px] transition-colors",
        current
          ? "bg-accent-soft text-accent"
          : "text-muted hover:bg-panel-2 hover:text-fg",
      )}
      // +16 aligns page titles with folder names (chevron width) at the same depth.
      style={{ paddingLeft: depth * INDENT + 24 }}
    >
      <span className="truncate">{meta.title}</span>
      {meta.isIndex && (
        <span className="ml-auto shrink-0 rounded border border-border px-1 text-[9px] uppercase tracking-wider text-faint">
          moc
        </span>
      )}
    </Link>
  );
}

function FolderNode({
  folder,
  depth,
  openSet,
  onToggle,
  currentPath,
}: {
  folder: TreeFolder;
  depth: number;
  openSet: Set<string>;
  onToggle: (path: string) => void;
  currentPath: string | null;
}) {
  const open = openSet.has(folder.path);
  return (
    <div>
      <button
        type="button"
        onClick={() => onToggle(folder.path)}
        title={open ? "Collapse folder" : "Expand folder"}
        className="group flex w-full items-center gap-1 rounded-md px-2 py-[3px] text-left text-[13px] text-muted transition-colors hover:bg-panel-2 hover:text-fg"
        style={{ paddingLeft: depth * INDENT + 8 }}
      >
        <ChevronRightIcon
          size={12}
          className={clsx(
            "shrink-0 text-faint transition-transform duration-150 group-hover:text-accent",
            open && "rotate-90",
          )}
        />
        <span className="truncate">{folder.name}</span>
        <span className="ml-auto shrink-0 text-[10px] text-faint">
          {countPages(folder)}
        </span>
      </button>
      {open && (
        <div>
          {folder.folders.map((child) => (
            <FolderNode
              key={child.path}
              folder={child}
              depth={depth + 1}
              openSet={openSet}
              onToggle={onToggle}
              currentPath={currentPath}
            />
          ))}
          {folder.pages.map((page) => (
            <PageRow
              key={page.path}
              meta={page}
              depth={depth + 1}
              current={page.path === currentPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function TreePanel({
  openSet,
  onToggle,
}: {
  openSet: Set<string>;
  onToggle: (path: string) => void;
}) {
  const { data } = useWikiData();
  const currentPath = useCurrentPagePath();

  if (!data) return <SkeletonRows />;

  return (
    <div className="px-1 py-2">
      {data.tree.folders.map((folder) => (
        <FolderNode
          key={folder.path}
          folder={folder}
          depth={0}
          openSet={openSet}
          onToggle={onToggle}
          currentPath={currentPath}
        />
      ))}
      {data.tree.pages.map((page) => (
        <PageRow
          key={page.path}
          meta={page}
          depth={0}
          current={page.path === currentPath}
        />
      ))}
    </div>
  );
}
