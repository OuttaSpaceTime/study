// Deterministic topic colors, shared by graph nodes, tags, and nav accents.
// Curated palette indexed by a stable hash of the top-level folder name.

// Medium-dark, saturated hues — readable as text and chips on the light theme.
const PALETTE = [
  "#4a5fc1", // indigo
  "#34855a", // green
  "#b07a23", // amber
  "#c25069", // rose
  "#7d56c2", // violet
  "#2387a8", // cyan
  "#c2682f", // orange
  "#1f8f7c", // teal
  "#67729e", // lavender
  "#b3539a", // pink
  "#7a8a44", // sage
  "#a08327", // gold
  "#3186c2", // sky
];

export function topicColor(folder: string): string {
  const topic = folder.split("/")[0] || "wiki";
  let hash = 0;
  for (let i = 0; i < topic.length; i++) {
    hash = (hash * 31 + topic.charCodeAt(i)) >>> 0;
  }
  // The modulo is always in range; the fallback only satisfies
  // noUncheckedIndexedAccess.
  return PALETTE[hash % PALETTE.length] ?? "#4a5fc1";
}
