import { Fragment } from "react";
import Link from "next/link";

/**
 * Linked breadcrumb: "wiki" (→ /) then each folder segment (→ /wiki/<path>).
 * Pass the folder path of the current page (or the parent path for a folder
 * view); the current item itself is rendered as the H1 below, not here.
 */
export default function Breadcrumb({ folder }: { folder: string }) {
  const segments = folder ? folder.split("/") : [];
  return (
    <nav className="flex flex-wrap items-center gap-1.5 text-[12px] text-faint">
      <Link href="/" className="transition-colors hover:text-fg">
        wiki
      </Link>
      {segments.map((segment, i) => {
        const path = segments.slice(0, i + 1).join("/");
        return (
          <Fragment key={path}>
            <span aria-hidden>/</span>
            <Link
              href={`/wiki/${path}`}
              className="transition-colors hover:text-fg"
            >
              {segment}
            </Link>
          </Fragment>
        );
      })}
    </nav>
  );
}
