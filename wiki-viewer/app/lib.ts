// Dashboard helpers kept pure so the review-queue rules are unit-testable.
import type { PageMeta } from "@/lib/types";

export function dueForReview(pages: PageMeta[], today: string): PageMeta[] {
  return pages
    .filter((p) => p.nextReview !== "" && p.nextReview <= today)
    .sort((a, b) => a.nextReview.localeCompare(b.nextReview));
}
