"use client";

// CONTEXT state: "where am I, what is around me, how do I go up / elsewhere".
// On a page: breadcrumb stack, current-folder siblings + subfolders, link lists.
// Off a page (dashboard / folder view): top-level topics overview.

import { useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import {
  useCurrentPagePath,
  useWikiData,
} from "@/components/providers/WikiDataProvider";
import { topicColor } from "@/lib/colors";
import type { PageMeta, TreeFolder } from "@/lib/types";
import { ChevronRightIcon } from "./icons";
import { countPages, findFolder, topLevelFolder } from "./lib";
import PageSections from "./PageSections";
import SkeletonRows from "./SkeletonRows";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-2 pb-1 pt-4 text-[11px] font-medium uppercase tracking-wider text-faint">
      {children}
    </div>
  );
}

/** Breadcrumb stack: root → folder segments → current page title. */
function YouAreHere({ meta }: { meta: PageMeta }) {
  const segments = meta.folder ? meta.folder.split("/") : [];
  return (
    <>
      <SectionLabel>You are here</SectionLabel>
      <div className="px-2 text-[13px] leading-6">
        <div>
          <Link
            href="/"
            className="text-muted transition-colors hover:text-fg"
          >
            wiki
          </Link>
        </div>
        {segments.map((segment, i) => (
          <div
            key={i}
            className="flex items-center"
            style={{ paddingLeft: (i + 1) * 10 }}
          >
            <span className="mr-1 text-faint">└</span>
            <Link
              href={`/wiki/${segments.slice(0, i + 1).join("/")}`}
              className="truncate text-muted transition-colors hover:text-fg"
            >
              {segment}
            </Link>
          </div>
        ))}
        <div
          className="flex items-center"
          style={{ paddingLeft: (segments.length + 1) * 10 }}
        >
          <span className="mr-1 text-faint">└</span>
          <span className="truncate font-medium text-fg">{meta.title}</span>
        </div>
      </div>
    </>
  );
}

function SiblingRow({ meta, current }: { meta: PageMeta; current: boolean }) {
  return (
    <Link
      href={`/wiki/${meta.path}`}
      className={clsx(
        "flex items-center gap-2 rounded-md px-2 py-1 text-[13px] transition-colors",
        current
          ? "bg-accent-soft text-accent"
          : "text-muted hover:bg-panel-2 hover:text-fg",
      )}
    >
      <span
        className="h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: topicColor(meta.folder) }}
      />
      <span className="truncate">{meta.title}</span>
    </Link>
  );
}

/** Disclosure row: clicking expands the subfolder inline (pages + nested folders). */
function SubfolderRow({
  folder,
  currentPath,
  depth = 0,
}: {
  folder: TreeFolder;
  currentPath: string;
  depth?: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        title={open ? "Collapse folder" : "Expand folder"}
        className="group flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-[13px] text-muted transition-colors hover:bg-panel-2 hover:text-fg"
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        <ChevronRightIcon
          size={12}
          className={clsx(
            "shrink-0 text-faint transition-transform group-hover:text-accent",
            open && "rotate-90",
          )}
        />
        <span className="truncate">{folder.name}</span>
        <span className="ml-auto shrink-0 text-[10px] text-faint">
          {countPages(folder)}
        </span>
      </button>
      {open && (
        <>
          {folder.pages.map((page) => (
            <div key={page.path} style={{ paddingLeft: (depth + 1) * 14 }}>
              <SiblingRow meta={page} current={page.path === currentPath} />
            </div>
          ))}
          {folder.folders.map((child) => (
            <SubfolderRow
              key={child.path}
              folder={child}
              currentPath={currentPath}
              depth={depth + 1}
            />
          ))}
        </>
      )}
    </>
  );
}

/** A row in the Outgoing / Linked-from lists: title + faint topic label. */
function LinkRow({ path, byPath }: { path: string; byPath: Map<string, PageMeta> }) {
  const meta = byPath.get(path);
  const title = meta?.title ?? path.split("/").pop() ?? path;
  return (
    <Link
      href={`/wiki/${path}`}
      className="flex items-baseline gap-2 rounded-md px-2 py-1 text-[13px] text-muted transition-colors hover:bg-panel-2 hover:text-fg"
    >
      <span className="truncate">{title}</span>
      <span className="ml-auto shrink-0 text-[10px] text-faint">
        {topLevelFolder(path)}
      </span>
    </Link>
  );
}

function LinkList({
  label,
  paths,
  byPath,
}: {
  label: string;
  paths: string[];
  byPath: Map<string, PageMeta>;
}) {
  if (paths.length === 0) return null;
  return (
    <>
      <SectionLabel>{label}</SectionLabel>
      <div className="px-1">
        {paths.map((path) => (
          <LinkRow key={path} path={path} byPath={byPath} />
        ))}
      </div>
    </>
  );
}

/** Dashboard / folder view: every top-level topic as a row. */
function TopicsOverview({ tree }: { tree: TreeFolder }) {
  return (
    <>
      <SectionLabel>Topics</SectionLabel>
      <div className="px-1">
        {tree.folders.map((folder) => (
          <Link
            key={folder.path}
            href={`/wiki/${folder.path}`}
            className="flex items-center gap-2 rounded-md px-2 py-1 text-[13px] text-muted transition-colors hover:bg-panel-2 hover:text-fg"
          >
            <span
              className="h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ backgroundColor: topicColor(folder.path) }}
            />
            <span className="truncate">{folder.name}</span>
            <span className="ml-auto shrink-0 text-[10px] text-faint">
              {countPages(folder)}
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}

export default function ContextPanel() {
  const { data, byPath } = useWikiData();
  const currentPath = useCurrentPagePath();

  if (!data) return <SkeletonRows />;

  const meta = currentPath ? byPath.get(currentPath) : undefined;
  if (!meta) return <TopicsOverview tree={data.tree} />;

  const folder = findFolder(data.tree, meta.folder);
  const folderName = meta.folder ? (meta.folder.split("/").pop() ?? meta.folder) : "wiki";

  return (
    <div className="pb-2">
      <YouAreHere meta={meta} />

      {folder && (
        <>
          <SectionLabel>{folderName}</SectionLabel>
          <div className="px-1">
            {folder.pages.map((page) => (
              <div key={page.path}>
                <SiblingRow meta={page} current={page.path === meta.path} />
                {page.path === meta.path && (
                  <PageSections
                    path={page.path}
                    sections={page.sections}
                    paddingLeft={26}
                  />
                )}
              </div>
            ))}
            {folder.folders.map((child) => (
              <SubfolderRow
                key={child.path}
                folder={child}
                currentPath={meta.path}
              />
            ))}
          </div>
        </>
      )}

      <LinkList label="Outgoing" paths={meta.outbound} byPath={byPath} />
      <LinkList label="Linked from" paths={meta.inbound} byPath={byPath} />
    </div>
  );
}
