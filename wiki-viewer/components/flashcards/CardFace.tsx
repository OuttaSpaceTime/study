import clsx from "clsx";
import { STATE_COLORS, stateOf } from "./lib";
import type { Card } from "@/lib/types";

/** Card fields are simple HTML authored for Anki, from the local deck. */
export function CardHtml({ html, className }: { html: string; className?: string }) {
  return (
    <div
      className={clsx("card-html", className)}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function StateDot({ card }: { card: Card }) {
  const state = stateOf(card);
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-faint">
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: STATE_COLORS[state] }}
      />
      {state}
    </span>
  );
}

export function CardMeta({ card }: { card: Card }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-faint">
      <StateDot card={card} />
      <span>due {card.due}</span>
      {card.lastReview && <span>last seen {card.lastReview}</span>}
      {card.interval > 0 && <span>interval {Math.round(card.interval)}d</span>}
      <span>{card.reps} reps</span>
      {card.lapses > 0 && (
        <span className={clsx(card.lapses >= 5 && "font-medium text-[#c2405a]")}>
          {card.lapses} lapses{card.lapses >= 5 && " · leech"}
        </span>
      )}
      {card.stability > 0 && (
        <span>
          stability {card.stability.toFixed(1)}d · difficulty{" "}
          {card.difficulty.toFixed(1)}
        </span>
      )}
      {card.tags.length > 0 && (
        <span className="flex flex-wrap gap-1">
          {card.tags.map((tag) => (
            <span key={tag} className="rounded bg-panel-2 px-1.5 py-px">
              {tag}
            </span>
          ))}
        </span>
      )}
    </div>
  );
}
