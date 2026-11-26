import type { Metadata } from "next";
import Explorer from "@/components/flashcards/Explorer";
import { getAllCards } from "@/lib/flashcards";
import { getCalibration } from "@/lib/calibration";

export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "Flashcards · Study Wiki" };

export default async function FlashcardsPage() {
  const [cards, calibration] = await Promise.all([getAllCards(), getCalibration()]);
  return <Explorer cards={cards} calibration={calibration} />;
}
