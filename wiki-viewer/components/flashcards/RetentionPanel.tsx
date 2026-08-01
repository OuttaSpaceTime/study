import clsx from "clsx";
import { STATE_COLORS, type StateKey } from "./lib";
import type { Calibration } from "@/lib/types";

const VERDICT_COLORS: Record<Calibration["verdict"], string> = {
  "over-difficult": "#c2405a",
  calibrated: "#2f7d5b",
  "under-difficult": "#b4541a",
  "low-signal": "#818794",
};

export default function RetentionPanel({
  calibration,
  states,
  activeState,
  onStateClick,
  total,
}: {
  calibration: Calibration | null;
  states: { state: StateKey; count: number }[];
  activeState: StateKey | null;
  onStateClick: (state: StateKey) => void;
  total: number;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
      <div className="rounded-xl border border-border bg-panel p-4">
        <div className="text-[11px] uppercase tracking-wider text-faint">
          True retention{calibration && ` · ${calibration.windowDays}d`}
        </div>
        {calibration === null ? (
          <div className="mt-2 max-w-48 text-xs text-faint">
            Unavailable — run <code>scripts/study-calibration</code> to check.
          </div>
        ) : (
          <>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tabular-nums text-fg">
                {calibration.retention === null
                  ? "—"
                  : `${Math.round(calibration.retention * 100)}%`}
              </span>
              <span
                className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                style={{
                  color: VERDICT_COLORS[calibration.verdict],
                  backgroundColor: `${VERDICT_COLORS[calibration.verdict]}1a`,
                }}
              >
                {calibration.verdict}
                {calibration.marginal && " (marginal)"}
              </span>
            </div>
            <div className="mt-1 text-xs text-faint">
              {calibration.passed}/{calibration.reviews} reviews passed
            </div>
          </>
        )}
      </div>

      <div className="rounded-xl border border-border bg-panel p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-[11px] uppercase tracking-wider text-faint">
            Deck state
          </span>
          <span className="text-xs text-faint">{total} cards</span>
        </div>

        <div className="flex h-2.5 overflow-hidden rounded-full bg-panel-2">
          {states.map(({ state, count }) => (
            <button
              key={state}
              type="button"
              onClick={() => onStateClick(state)}
              title={`${count} ${state}`}
              className={clsx(
                "h-full transition-all duration-300 hover:opacity-80",
                activeState && activeState !== state && "opacity-30",
              )}
              style={{
                width: `${(count / Math.max(total, 1)) * 100}%`,
                backgroundColor: STATE_COLORS[state],
              }}
            />
          ))}
        </div>

        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
          {states.map(({ state, count }) => (
            <button
              key={state}
              type="button"
              onClick={() => onStateClick(state)}
              className={clsx(
                "flex items-center gap-1.5 text-xs transition-opacity",
                activeState && activeState !== state
                  ? "opacity-40 hover:opacity-70"
                  : "opacity-100",
              )}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: STATE_COLORS[state] }}
              />
              <span className="text-muted">{state}</span>
              <span className="font-medium tabular-nums text-fg">{count}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
