import { topicColor } from "@/lib/colors";

/** Tiny rounded pill; topicColor at ~15% opacity background. */
export default function TagChip({ tag }: { tag: string }) {
  const color = topicColor(tag);
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-px text-[11px] font-medium leading-4"
      style={{ backgroundColor: `${color}26`, color }}
    >
      {tag}
    </span>
  );
}
