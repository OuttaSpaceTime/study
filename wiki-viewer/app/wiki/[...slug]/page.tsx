import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPage, getWikiIndex } from "@/lib/wiki";
import type { TreeFolder } from "@/lib/types";
import Article from "@/components/article/Article";
import FolderView from "@/components/article/FolderView";

// Re-read the wiki from disk on every request so edits show on reload.
export const dynamic = "force-dynamic";

interface RouteParams {
  slug: string[];
}

function wikiPathFrom(slug: string[]): string {
  return slug.map(decodeURIComponent).join("/");
}

function findFolder(root: TreeFolder, path: string): TreeFolder | null {
  if (root.path === path) return root;
  for (const child of root.folders) {
    if (path === child.path || path.startsWith(`${child.path}/`)) {
      return findFolder(child, path);
    }
  }
  return null;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<RouteParams>;
}): Promise<Metadata> {
  const { slug } = await params;
  const wikiPath = wikiPathFrom(slug);
  const index = await getWikiIndex();
  const page = index.pages.find((p) => p.path === wikiPath);
  return { title: `${page?.title ?? wikiPath} · Study Wiki` };
}

export default async function WikiSlugPage({
  params,
}: {
  params: Promise<RouteParams>;
}) {
  const { slug } = await params;
  const wikiPath = wikiPathFrom(slug);
  const [page, index] = await Promise.all([
    getPage(wikiPath),
    getWikiIndex(),
  ]);

  if (page) {
    // MOC pages survive only as graph ghosts; their refs let wikilinks
    // targeting a MOC resolve to the folder view instead of breaking.
    const mocs = index.graph.nodes
      .filter((n) => n.isIndex)
      .map((n) => ({ path: n.id, folder: n.folder }));
    return <Article page={page} pages={index.pages} mocs={mocs} />;
  }

  const folder = wikiPath ? findFolder(index.tree, wikiPath) : null;
  if (folder) {
    return <FolderView folder={folder} />;
  }

  notFound();
}
