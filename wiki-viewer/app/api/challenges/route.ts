import { getChallengeIndex } from "@/lib/challenges";

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await getChallengeIndex());
}
