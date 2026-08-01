"use client";

import { useState } from "react";
import clsx from "clsx";
import FlashcardModal from "./FlashcardModal";
import RetentionPanel from "./RetentionPanel";
import { CardHtml, StateDot } from "./CardFace";
import { filterCards, stateCounts, tagCounts, type CardFilters } from "./lib";
import type { Calibration, Card } from "@/lib/types";

const NO_FILTERS: CardFilters = { query: "", state: null, tag: null, deck: null };

export default function Explorer({
  cards,
  calibration,
}: {
  cards: Card[];
  calibration: Calibration | null;
}) {
  const [filters, setFilters] = useState<CardFilters>(NO_FILTERS);
  const [browseAt, setBrowseAt] = useState<number | null>(null);

  const states = stateCounts(cards);
  const tags = tagCounts(cards).slice(0, 24);
  const decks = [...new Set(cards.map((c) => c.deck))].sort();
  const visible = filterCards(cards, filters);

  const toggle = (key: "state" | "tag" | "deck", value: string) =>
    setFilters((current) => ({
      ...current,
      [key]: current[key] === value ? null : value,
    }));

  const filtered =
    filters.query !== "" ||
    filters.state !== null ||
    filters.tag !== null ||
    filters.deck !== null;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-fg">Flashcards</h1>
        <p className="mt-1 text-sm text-muted">
          {cards.length} cards · browse, filter, and flip through the deck
        </p>
      </header>

      <div className="mb-6">
        <RetentionPanel
          calibration={calibration}
          states={states}
          total={cards.length}
          activeState={filters.state}
          onStateClick={(state) => toggle("state", state)}
        />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={filters.query}
          onChange={(event) =>
            setFilters((current) => ({ ...current, query: event.target.value }))
          }
          placeholder="Search fronts, backs, tags…"
          className="min-w-56 flex-1 rounded-lg border border-border bg-panel px-3 py-1.5 text-sm text-fg outline-none transition-colors placeholder:text-faint focus:border-accent"
        />
        {decks.length > 1 &&
          decks.map((deck) => (
            <button
              key={deck}
              type="button"
              onClick={() => toggle("deck", deck)}
              className={clsx(
                "rounded-lg border px-2.5 py-1.5 text-xs transition-colors",
                filters.deck === deck
                  ? "border-accent bg-accent-soft text-accent"
                  : "border-border text-muted hover:bg-panel-2",
              )}
            >
              {deck}
            </button>
          ))}
        <button
          type="button"
          disabled={visible.length === 0}
          onClick={() => setBrowseAt(0)}
          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          Flip through {visible.length}
        </button>
      </div>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {tags.map(({ tag, count }) => (
          <button
            key={tag}
            type="button"
            onClick={() => toggle("tag", tag)}
            className={clsx(
              "rounded-full px-2.5 py-1 text-[11px] transition-colors",
              filters.tag === tag
                ? "bg-accent text-white"
                : "bg-panel-2 text-muted hover:text-fg",
            )}
          >
            {tag}
            <span className="ml-1 opacity-60">{count}</span>
          </button>
        ))}
        {filtered && (
          <button
            type="button"
            onClick={() => setFilters(NO_FILTERS)}
            className="rounded-full px-2.5 py-1 text-[11px] text-faint underline-offset-2 hover:underline"
          >
            clear filters
          </button>
        )}
      </div>

      {visible.length === 0 ? (
        <p className="py-16 text-center text-sm text-faint">
          No cards match these filters.
        </p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {visible.map((card, i) => (
            <li key={card.id}>
              <button
                type="button"
                onClick={() => setBrowseAt(i)}
                className="card-rise flex h-full w-full flex-col rounded-xl border border-border bg-panel p-4 text-left shadow-sm transition-shadow hover:shadow-md"
                style={{ animationDelay: `${Math.min(i, 14) * 25}ms` }}
              >
                <StateDot card={card} />
                <CardHtml
                  html={card.front}
                  className="mt-2 line-clamp-4 text-sm text-fg"
                />
                {card.tags.length > 0 && (
                  <div className="mt-auto flex flex-wrap gap-1 pt-3">
                    {card.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded bg-panel-2 px-1.5 py-px text-[10px] text-faint"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      {browseAt !== null && (
        <FlashcardModal
          cards={visible}
          startAt={browseAt}
          title="Flashcard browser"
          subtitle={`${visible.length} of ${cards.length} cards${
            filtered ? " (filtered)" : ""
          }`}
          onClose={() => setBrowseAt(null)}
        />
      )}
    </div>
  );
}
