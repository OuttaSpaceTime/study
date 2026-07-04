import { NextResponse } from "next/server";
import { getWikiIndex } from "@/lib/wiki";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(await getWikiIndex());
}
