"""Semantic search against wiki embeddings using Ollama + cosine similarity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.wiki.embed import cosine_similarity, get_embedding, load_embeddings


def search(
    query: str,
    wiki_dir: Path,
    top: int = 5,
    threshold: float = 0.3,
) -> list[dict]:
    """Search wiki embeddings for query, returning top results above threshold."""
    embeddings = load_embeddings(wiki_dir)
    if not embeddings:
        return []

    query_vec = get_embedding(query)

    results = []
    for path, vec in embeddings.items():
        score = cosine_similarity(query_vec, vec)
        if score >= threshold:
            results.append({"path": path, "score": round(score, 4)})

    results.sort(key=lambda x: -x["score"])
    return results[:top]


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic wiki search")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--top", type=int, default=5, help="Number of results")
    parser.add_argument("--threshold", type=float, default=0.3, help="Minimum similarity")
    parser.add_argument("--wiki-dir", default="wiki", help="Wiki directory")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    wiki_dir = Path(args.wiki_dir)
    embeddings_file = wiki_dir / ".embeddings.json"
    if not embeddings_file.exists():
        print("No embeddings found. Run wiki-write first.", file=sys.stderr)
        sys.exit(1)

    results = search(args.query, wiki_dir, top=args.top, threshold=args.threshold)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        if not results:
            print(f"No results above threshold {args.threshold} for: {args.query}")
        else:
            for r in results:
                print(f"  {r['score']:.4f}  {r['path']}")


if __name__ == "__main__":
    main()
