import type { Metadata } from "next";
import Explorer from "@/components/flashcards/Explorer";
import { getAllCards } from "@/lib/flashcards";
import { getCalibration } from "@/lib/calibration";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Flashcards · Study Wiki" };

export default async function FlashcardsPage() {
  return <Explorer cards={getAllCards()} calibration={await getCalibration()} />;
}
