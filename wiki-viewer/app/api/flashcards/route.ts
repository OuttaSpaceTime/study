import { NextResponse } from "next/server";
import { getCardsByIds, getCardsByTags } from "@/lib/flashcards";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  const split = (key: string) =>
    (params.get(key) ?? "").split(",").map((v) => v.trim()).filter(Boolean);

  const ids = split("ids");
  if (ids.length > 0) {
    return NextResponse.json({ cards: getCardsByIds(ids), matchedBy: "ids" });
  }
  return NextResponse.json({
    cards: getCardsByTags(split("tags")),
    matchedBy: "tags",
  });
}
