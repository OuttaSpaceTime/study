// Dashboard helpers kept pure so the review-queue rules are unit-testable.
import type { PageMeta } from "@/lib/types";

// Mirrors get_due_entries on the Python side: no-study pages leave the study
// loop, so they must not appear in the review queue even when overdue.
export function dueForReview(pages: PageMeta[], today: string): PageMeta[] {
  return pages
    .filter(
      (p) =>
        !p.tags.includes("no-study") &&
        p.nextReview !== "" &&
        p.nextReview <= today,
    )
    .sort((a, b) => a.nextReview.localeCompare(b.nextReview));
}
