"use client";

import { useEffect, useState } from "react";
import FlashcardModal from "@/components/flashcards/FlashcardModal";
import type { Card } from "@/lib/types";

type Load =
  | { status: "loading" }
  | { status: "ready"; cards: Card[]; matchedBy: "ids" | "tags" }
  | { status: "failed" };

/**
 * Opens the page's flashcards in a modal. Cards load on first open, so an
 * article render never waits on the deck.
 */
export default function FlashcardLauncher({
  cardIds,
  pageTitle,
  tags,
}: {
  cardIds: string[];
  pageTitle: string;
  tags: string[];
}) {
  const [open, setOpen] = useState(false);
  const [load, setLoad] = useState<Load>({ status: "loading" });

  const hasLinked = cardIds.length > 0;

  useEffect(() => {
    // Retry on reopen after a failure, so a transient error isn't permanent.
    if (!open || load.status === "ready") return;
    const query = hasLinked
      ? `ids=${cardIds.join(",")}`
      : `tags=${tags.join(",")}`;
    let active = true;
    fetch(`/api/flashcards?${query}`)
      .then((response) => response.json())
      .then((data: { cards: Card[]; matchedBy: "ids" | "tags" }) => {
        if (active) setLoad({ status: "ready", ...data });
      })
      .catch(() => {
        if (active) setLoad({ status: "failed" });
      });
    return () => {
      active = false;
    };
  }, [open, load.status, cardIds, tags, hasLinked]);

  function close() {
    setOpen(false);
    if (load.status === "failed") setLoad({ status: "loading" });
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded border border-border px-1.5 py-px transition-colors hover:border-accent hover:text-accent"
      >
        {hasLinked
          ? `${cardIds.length} flashcard${cardIds.length === 1 ? "" : "s"}`
          : "explore flashcards"}
      </button>
      {open && (
        <FlashcardModal
          cards={load.status === "ready" ? load.cards : []}
          loading={load.status === "loading"}
          error={load.status === "failed"}
          title={pageTitle}
          subtitle={
            load.status === "ready" && load.matchedBy === "tags"
              ? "related cards, matched by tag"
              : "cards linked to this page"
          }
          onClose={close}
        />
      )}
    </>
  );
}
