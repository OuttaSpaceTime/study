// No "use client" directive: this is only ever rendered by client components
// (the article launcher and the explorer), so it joins their bundle already.
// Declaring it an entry would force every prop to be serializable, and onClose
// is a plain callback.
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import { CardHtml, CardMeta, StateDot } from "./CardFace";
import type { Card } from "@/lib/types";

type Mode = "overview" | "flip";

export default function FlashcardModal({
  cards,
  title,
  subtitle,
  loading = false,
  error = false,
  startAt,
  onClose,
}: {
  cards: Card[];
  title: string;
  subtitle?: string;
  loading?: boolean;
  error?: boolean;
  /** Given, the modal opens flipping through the deck from this card. */
  startAt?: number;
  onClose: () => void;
}) {
  const [mode, setMode] = useState<Mode>(startAt === undefined ? "overview" : "flip");
  const [index, setIndex] = useState(startAt ?? 0);
  const [flipped, setFlipped] = useState(false);
  const [revealed, setRevealed] = useState<Set<string>>(new Set());

  const count = cards.length;
  const step = useCallback(
    (delta: number) => {
      if (count === 0) return;
      setFlipped(false);
      // Wrap so a deck can be cycled without hunting for the ends.
      setIndex((i) => (i + delta + count) % count);
    },
    [count],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") return onClose();
      if (mode !== "flip") return;
      if (event.key === "ArrowRight") return step(1);
      if (event.key === "ArrowLeft") return step(-1);
      if (event.key !== " " && event.key !== "Enter") return;
      // Space and Enter belong to whatever is focused — claiming them here
      // unconditionally would make the close and next buttons unreachable.
      if (document.activeElement?.closest("button")) return;
      event.preventDefault();
      setFlipped((f) => !f);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, step, onClose]);

  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  function toggleReveal(id: string) {
    setRevealed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function enterFlip(at: number) {
    setIndex(at);
    setFlipped(false);
    setMode("flip");
  }

  const current = cards[index];

  return (
    <div
      className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-8"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="modal-panel flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-2xl border border-border bg-bg shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border bg-panel px-5 py-3.5">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-fg">{title}</h2>
            {subtitle && (
              <p className="truncate text-xs text-faint">{subtitle}</p>
            )}
          </div>

          <div className="ml-auto flex items-center gap-2">
            {count > 0 && (
              <div className="flex rounded-lg bg-panel-2 p-0.5 text-xs">
                {(["overview", "flip"] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setMode(value)}
                    className={clsx(
                      "rounded-md px-3 py-1 transition-colors",
                      mode === value
                        ? "bg-panel text-fg shadow-sm"
                        : "text-faint hover:text-fg",
                    )}
                  >
                    {value === "overview" ? "Overview" : "Flip through"}
                  </button>
                ))}
              </div>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded-md px-2 py-1 text-lg leading-none text-faint transition-colors hover:bg-panel-2 hover:text-fg"
            >
              ×
            </button>
          </div>
        </header>

        {loading ? (
          <div className="flex flex-1 items-center justify-center text-sm text-faint">
            <span className="pulse-soft">Loading cards…</span>
          </div>
        ) : error ? (
          <div className="flex flex-1 items-center justify-center px-8 text-center text-sm text-faint">
            Could not reach the flashcard deck. Close and reopen to retry.
          </div>
        ) : count === 0 ? (
          <div className="flex flex-1 items-center justify-center px-8 text-center text-sm text-faint">
            No flashcards linked to this page yet.
          </div>
        ) : mode === "overview" ? (
          <div className="flex-1 overflow-y-auto p-5">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {cards.map((card, i) => {
                const open = revealed.has(card.id);
                return (
                  <article
                    key={card.id}
                    className="card-rise group flex flex-col rounded-xl border border-border bg-panel p-4 shadow-sm transition-shadow hover:shadow-md"
                    style={{ animationDelay: `${Math.min(i, 12) * 35}ms` }}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <StateDot card={card} />
                      <button
                        type="button"
                        onClick={() => enterFlip(i)}
                        className="text-[11px] text-faint opacity-0 transition-opacity hover:text-accent group-hover:opacity-100"
                      >
                        flip through from here →
                      </button>
                    </div>
                    <CardHtml
                      html={card.front}
                      className="text-sm font-medium text-fg"
                    />
                    <button
                      type="button"
                      onClick={() => toggleReveal(card.id)}
                      className="mt-3 self-start text-xs text-accent transition-colors hover:underline"
                    >
                      {open ? "hide answer" : "show answer"}
                    </button>
                    <div
                      className={clsx(
                        "reveal grid text-sm text-muted",
                        open ? "reveal-open" : "reveal-closed",
                      )}
                    >
                      <div className="overflow-hidden">
                        <div className="border-t border-border pt-3">
                          <CardHtml html={card.back} />
                          <div className="mt-3">
                            <CardMeta card={card} />
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        ) : (
          current && (
            <div className="flex flex-1 flex-col overflow-hidden">
              <div className="flex flex-1 items-center justify-center overflow-y-auto px-5 py-6">
                <div className="flex w-full max-w-3xl flex-col items-center">
                  <div
                    className={clsx("flip-scene w-full", flipped && "is-flipped")}
                    onClick={() => setFlipped((f) => !f)}
                    role="button"
                    tabIndex={-1}
                    aria-label="Flip card"
                  >
                    <div className="flip-inner">
                      <div className="flip-face rounded-2xl border border-border bg-panel p-8 shadow-lg">
                        <div className="mb-4 text-[11px] uppercase tracking-widest text-faint">
                          Question
                        </div>
                        <CardHtml
                          html={current.front}
                          className="text-lg leading-relaxed text-fg"
                        />
                        <div className="mt-6 text-xs text-faint">
                          click, space, or enter to reveal
                        </div>
                      </div>
                      <div className="flip-face flip-back rounded-2xl border border-border bg-panel p-8 shadow-lg">
                        <div className="mb-4 text-[11px] uppercase tracking-widest text-faint">
                          Answer
                        </div>
                        <CardHtml
                          html={current.back}
                          className="text-base leading-relaxed text-fg"
                        />
                        <div className="mt-6 border-t border-border pt-3">
                          <CardMeta card={current} />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <footer className="flex shrink-0 items-center gap-4 border-t border-border bg-panel px-5 py-3">
                <button
                  type="button"
                  onClick={() => step(-1)}
                  className="rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:bg-panel-2 hover:text-fg"
                >
                  ← prev
                </button>
                <div className="flex flex-1 items-center gap-3">
                  <div className="h-1 flex-1 overflow-hidden rounded-full bg-panel-2">
                    <div
                      className="h-full rounded-full bg-accent transition-all duration-300"
                      style={{ width: `${((index + 1) / count) * 100}%` }}
                    />
                  </div>
                  <span className="shrink-0 font-mono text-xs text-faint">
                    {index + 1} / {count}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => step(1)}
                  className="rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:bg-panel-2 hover:text-fg"
                >
                  next →
                </button>
              </footer>
            </div>
          )
        )}
      </div>
    </div>
  );
}
