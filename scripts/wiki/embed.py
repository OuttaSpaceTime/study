"""Ollama embedding and cosine similarity."""

from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path

from scripts.wiki.frontmatter import parse_frontmatter


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_embedding(
    text: str, base_url: str = "http://localhost:11434"
) -> list[float]:
    """Get embedding vector from Ollama nomic-embed-text."""
    req = urllib.request.Request(
        f"{base_url}/api/embeddings",
        data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
    return resp["embedding"]


def load_embeddings(wiki_dir: Path) -> dict:
    """Load embeddings from wiki/.embeddings.json."""
    path = Path(wiki_dir) / ".embeddings.json"
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def save_embeddings(wiki_dir: Path, embeddings: dict) -> None:
    """Save embeddings to wiki/.embeddings.json."""
    path = Path(wiki_dir) / ".embeddings.json"
    with open(path, "w") as f:
        json.dump(embeddings, f, ensure_ascii=False)
        f.write("\n")


def update_embeddings(
    wiki_dir: Path,
    page_path: Path,
    base_url: str = "http://localhost:11434",
) -> None:
    """Embed a page and update the embeddings file."""
    wiki_dir = Path(wiki_dir)
    content = page_path.read_text()
    _, body = parse_frontmatter(content)

    vector = get_embedding(body[:2000], base_url)

    embeddings = load_embeddings(wiki_dir)
    rel_key = str(page_path.relative_to(wiki_dir)).removesuffix(".md")
    embeddings[rel_key] = vector
    save_embeddings(wiki_dir, embeddings)
