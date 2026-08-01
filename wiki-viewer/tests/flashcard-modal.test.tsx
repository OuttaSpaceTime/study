// Rendered with renderToStaticMarkup, so effects never run — this asserts the
// first paint of each mode and state, not the post-interaction transitions.
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import FlashcardModal from "@/components/flashcards/FlashcardModal";
import { makeCard } from "./fixtures";

const CARDS = [
  makeCard({ id: "a", front: "front A", back: "back A" }),
  makeCard({ id: "b", front: "front B", back: "back B" }),
  makeCard({ id: "c", front: "front C", back: "back C" }),
];

function render(props: Partial<Parameters<typeof FlashcardModal>[0]> = {}) {
  return renderToStaticMarkup(
    <FlashcardModal cards={CARDS} title="Test Page" onClose={() => {}} {...props} />,
  );
}

describe("FlashcardModal", () => {
  it("shows a loading state instead of an empty deck while cards are fetching", () => {
    const html = render({ cards: [], loading: true });
    expect(html).toContain("Loading cards");
    expect(html).not.toContain("No flashcards linked");
  });

  it("explains an empty result rather than rendering a blank panel", () => {
    const html = render({ cards: [], loading: false });
    expect(html).toContain("No flashcards linked to this page yet");
  });

  it("hides the mode switch when there is nothing to browse", () => {
    expect(render({ cards: [] })).not.toContain("Flip through");
  });

  it("renders every card front in overview mode", () => {
    const html = render();
    for (const card of CARDS) expect(html).toContain(card.front);
  });

  it("keeps answers behind a reveal in overview mode", () => {
    const html = render();
    expect(html).toContain("show answer");
    // The back is in the DOM but collapsed, so the grid does not jump on reveal.
    expect(html).toContain("reveal-closed");
  });

  it("renders card HTML as markup, not escaped text", () => {
    const html = render({ cards: [makeCard({ front: "a <code>cookie</code>" })] });
    expect(html).toContain("<code>cookie</code>");
  });

  it("shows both faces and the position in flip mode", () => {
    const html = render({ startAt: 0 });
    expect(html).toContain("Question");
    expect(html).toContain("Answer");
    expect(html).toContain("1 / 3");
  });

  it("opens flip mode at the requested card", () => {
    const html = render({ startAt: 2 });
    expect(html).toContain("front C");
    expect(html).toContain("3 / 3");
  });

  it("starts unflipped so the answer is not showing", () => {
    expect(render({ startAt: 0 })).not.toContain("is-flipped");
  });

  it("marks a card with five or more lapses as a leech", () => {
    const html = render({ startAt: 0, cards: [makeCard({ lapses: 7 })] });
    expect(html).toContain("7 lapses");
    expect(html).toContain("leech");
  });

  it("does not call a card with few lapses a leech", () => {
    const html = render({ startAt: 0, cards: [makeCard({ lapses: 2 })] });
    expect(html).toContain("2 lapses");
    expect(html).not.toContain("leech");
  });

  it("labels a suspended card as suspended rather than by its stored state", () => {
    const html = render({
      startAt: 0,
      cards: [makeCard({ state: "review", suspended: true })],
    });
    expect(html).toContain("suspended");
  });

  it("names the page it was opened from", () => {
    expect(render({ title: "Row Locking" })).toContain("Row Locking");
  });
});
