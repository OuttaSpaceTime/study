// Server-only. The calibration verdict has one implementation, and it is
// `scripts/study-calibration` — the same one `/study` reads. Re-deriving
// retention here in TypeScript drifted within a day of being written (wrong
// min-review floor, no rating-discrimination guard, UTC instead of local days),
// so the viewer shells out (~50ms) rather than keep a second copy honest.
import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import type { Calibration } from "./types";

const run = promisify(execFile);

const REPO_ROOT = process.env.STUDY_ROOT ?? path.resolve(process.cwd(), "..");

interface CalibrationJson {
  verdict: Calibration["verdict"];
  marginal: boolean;
  true_retention: number | null;
  reviews: number;
  window_days: number;
  rating_mix: { again: number; hard: number; good: number; easy: number };
  reasons: string[];
}

/** Null when the script is unavailable — the panel degrades instead of 500ing. */
export async function getCalibration(): Promise<Calibration | null> {
  try {
    const { stdout } = await run("scripts/study-calibration", [], { cwd: REPO_ROOT });
    const data = JSON.parse(stdout) as CalibrationJson;
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
