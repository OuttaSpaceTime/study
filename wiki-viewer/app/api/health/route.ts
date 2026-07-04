import { CHALLENGES_ROOT } from "@/lib/challenges";
import { WIKI_ROOT } from "@/lib/wiki";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({
    ok: true,
    wikiRoot: WIKI_ROOT,
    challengesRoot: CHALLENGES_ROOT,
  });
}
