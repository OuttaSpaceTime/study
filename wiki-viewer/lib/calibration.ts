// Server-only. The calibration verdict has one implementation, and it lives in
// flashcard-mcp next to the deck it reads — the same code `/study` calls
// through `check_calibration`. Re-deriving retention here drifted within a day
// of being written (wrong min-review floor, no rating-discrimination guard, UTC
// instead of local days), so the viewer asks that repo's app server for the
// verdict (`calibration`) instead of keeping a second copy honest.
import { deckCall } from "./deck-client";
import type { Calibration } from "./types";

interface CalibrationJson {
  verdict: Calibration["verdict"];
  marginal: boolean;
  true_retention: number | null;
  reviews: number;
  window_days: number;
  rating_mix: { again: number; hard: number; good: number; easy: number };
  reasons: string[];
}

/** Null when the deck is unavailable — the panel degrades instead of 500ing. */
export async function getCalibration(): Promise<Calibration | null> {
  try {
    const data = await deckCall<CalibrationJson>("calibration");
    return {
      verdict: data.verdict,
      marginal: data.marginal,
      retention: data.true_retention,
      reviews: data.reviews,
      passed: data.rating_mix.good + data.rating_mix.easy,
      windowDays: data.window_days,
      reason: data.reasons[0] ?? "",
    };
  } catch {
    return null;
  }
}
