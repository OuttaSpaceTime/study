"""Per-machine location of the flashcard-mcp checkout.

The path differs between machines, so it is never committed: set
FLASHCARD_MCP_DIR in .env.local at the repo root (gitignored).
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env.local"


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if sep:
            values[key.strip()] = value.strip().strip("\"'")
    return values


def flashcard_mcp_dir(env_file: Path = ENV_FILE) -> Path:
    value = os.environ.get("FLASHCARD_MCP_DIR") or load_env_file(env_file).get(
        "FLASHCARD_MCP_DIR"
    )
    if not value:
        raise RuntimeError(
            f"FLASHCARD_MCP_DIR is not set. Write it to {env_file}, e.g.\n"
            f"    FLASHCARD_MCP_DIR=$HOME/Code/flashcard-mcp\n"
            "See 'Machine-local configuration' in README.md."
        )
    if value.startswith("$HOME/"):
        value = str(Path.home() / value[len("$HOME/") :])
    return Path(value).expanduser()


def master_db(env_file: Path = ENV_FILE) -> Path:
    override = os.environ.get("FLASHCARD_MASTER_DB")
    if override:
        return Path(override).expanduser()
    return flashcard_mcp_dir(env_file) / "prisma" / "master.db"
