"""Per-machine location of the agentic-spaced-repetition checkout.

The path differs between machines, so it is never committed: set
SRS_DIR in .env.local at the repo root (gitignored). FLASHCARD_MCP_DIR, the
name from before the rename, is still read when SRS_DIR is absent, so a machine
whose .env.local predates it keeps working after a pull.
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


DIR_KEYS = ("SRS_DIR", "FLASHCARD_MCP_DIR")  # preferred name first, old name as fallback


def srs_dir(env_file: Path = ENV_FILE) -> Path:
    file_values = load_env_file(env_file)
    # The environment wins over the file; within each, the new name wins over the old.
    value = next((v for key in DIR_KEYS if (v := os.environ.get(key))), None) or next(
        (v for key in DIR_KEYS if (v := file_values.get(key))), None
    )
    if not value:
        raise RuntimeError(
            f"SRS_DIR (or the old FLASHCARD_MCP_DIR) is not set. Write it to {env_file}, e.g.\n"
            f"    SRS_DIR=$HOME/Code/agentic-spaced-repetition\n"
            "See 'Machine-local configuration' in README.md."
        )
    if value.startswith("$HOME/"):
        value = str(Path.home() / value[len("$HOME/") :])
    return Path(value).expanduser()


def master_db(env_file: Path = ENV_FILE) -> Path:
    override = os.environ.get("FLASHCARD_MASTER_DB")
    if override:
        return Path(override).expanduser()
    return srs_dir(env_file) / "prisma" / "master.db"
