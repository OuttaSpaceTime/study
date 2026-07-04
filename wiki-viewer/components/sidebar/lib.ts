// Small pure helpers shared by the sidebar panels.
import type { TreeFolder } from "@/lib/types";

/** Locate a folder node by its path ("" returns the root). */
export function findFolder(root: TreeFolder, folderPath: string): TreeFolder | null {
  if (!folderPath) return root;
  let node = root;
  for (const segment of folderPath.split("/")) {
    const child = node.folders.find((f) => f.name === segment);
    if (!child) return null;
    node = child;
  }
  return node;
}

/** Recursive page count for a folder subtree. */
export function countPages(folder: TreeFolder): number {
  return (
    folder.pages.length +
    folder.folders.reduce((sum, child) => sum + countPages(child), 0)
  );
}

/** Top-level topic label for a wiki path, e.g. "rails/foreign-keys" → "rails". */
export function topLevelFolder(path: string): string {
  const parts = path.split("/");
  return parts.length > 1 ? (parts[0] ?? "wiki") : "wiki";
}
