"use client";

// Mini table-of-contents for the current page: its H2 headings as jump-links,
// with the heading currently in view highlighted (scroll-spy against <main>,
// the article's scroll container). Collapsible via an "On this page" toggle —
// expanded by default, the choice persisted in localStorage.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import clsx from "clsx";
import { slugifyHeading } from "@/lib/markdown";
import { ChevronRightIcon } from "./icons";

const TOGGLE_KEY = "wiki-viewer.page-sections-open";

/** Track which heading is currently at the top of the article viewport. */
function useActiveHeading(slugs: string[]): string | null {
  const [active, setActive] = useState<string | null>(null);
  const key = slugs.join("|");
  useEffect(() => {
    const scroller = document.querySelector("main");
    if (!scroller) return;
    const compute = () => {
      const line = scroller.getBoundingClientRect().top + 100;
      let current: string | null = null;
      for (const slug of slugs) {
        const el = document.getElementById(slug);
        if (el && el.getBoundingClientRect().top <= line) current = slug;
      }
      setActive(current ?? slugs[0] ?? null);
    };
    compute();
    scroller.addEventListener("scroll", compute, { passive: true });
    return () => scroller.removeEventListener("scroll", compute);
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return active;
}

/** Expanded by default; the stored preference is applied after hydration. */
function useSectionsOpen(): [boolean, () => void] {
  const [open, setOpen] = useState(true);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (window.localStorage.getItem(TOGGLE_KEY) === "closed") setOpen(false);
  }, []);
  const toggle = useCallback(() => {
    setOpen((prev) => {
      const next = !prev;
      try {
        window.localStorage.setItem(TOGGLE_KEY, next ? "open" : "closed");
      } catch {
        // Storage unavailable — state still works for this session.
      }
      return next;
    });
  }, []);
  return [open, toggle];
}

export default function PageSections({
  path,
  sections,
  paddingLeft,
}: {
  path: string;
  sections: string[];
  paddingLeft: number;
}) {
  const slugs = sections.map(slugifyHeading);
  const active = useActiveHeading(slugs);
  const [open, toggle] = useSectionsOpen();
  if (sections.length === 0) return null;
  return (
    <div className="py-0.5">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        title={open ? "Hide sections" : "Show sections"}
        className="group flex w-full items-center gap-1 rounded-md py-[3px] pr-2 text-left text-[10px] font-medium uppercase tracking-wider text-faint transition-colors hover:text-fg"
        style={{ paddingLeft }}
      >
        <ChevronRightIcon
          size={10}
          className={clsx(
            "shrink-0 transition-transform group-hover:text-accent",
            open && "rotate-90",
          )}
        />
        <span>On this page</span>
      </button>
      {open &&
        sections.map((section, i) => {
          const slug = slugs[i] ?? "";
          return (
            <Link
              key={slug}
              href={`/wiki/${path}#${slug}`}
              className={clsx(
                "flex items-center gap-1.5 rounded-md py-[3px] pr-2 text-[12px] transition-colors",
                active === slug ? "text-accent" : "text-faint hover:text-fg",
              )}
              style={{ paddingLeft: paddingLeft + 8 }}
            >
              <span
                className={clsx(
                  "h-3 w-px shrink-0",
                  active === slug ? "bg-accent" : "bg-border",
                )}
              />
              <span className="truncate">{section}</span>
            </Link>
          );
        })}
    </div>
  );
}
