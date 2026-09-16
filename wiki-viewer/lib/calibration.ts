// Server-only. The calibration verdict has one implementation, and it lives in
// flashcard-mcp next to the deck it reads — the same code `/study` calls
// through `check_calibration`. Re-deriving retention here drifted within a day
// of being written (wrong min-review floor, no rating-discrimination guard, UTC
// instead of local days), so the viewer shells out to that repo's CLI rather
// than keep a second copy honest. Going through the MCP protocol instead would
// mean spawning a stdio client per request.
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import type { Calibration } from "./types";

const run = promisify(execFile);

const MCP_DIR = process.env.FLASHCARD_MCP_DIR ??
  "/home/outtaspacetime/Code/flashcard-mcp";

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
    const { stdout } = await run(
      "npm",
      ["run", "dev:cli", "--silent", "--", "calibration"],
      { cwd: MCP_DIR },
    );
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
